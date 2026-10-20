"""
Scraper Zelda 40th Anniversary Concert
Parsea https://zelda.gameconcerts.com/ y extrae los conciertos de las dos secciones:
- Concert Tickets (en venta / info / on sale <fecha>)
- Sold-Out Concerts (agotados)
"""
import time

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

URL = "https://zelda.gameconcerts.com/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
TIMEOUT = 30

ESTADO_ENVENTA = "en_venta"
ESTADO_AGOTADO = "agotado"
ESTADO_PROXIMAMENTE = "proximamente"  # "on sale <fecha>"


def _parse_card(card, seccion, html_base):
    """Extrae los datos de una ficha <div class="col-... articletype-0 ...">"""
    ps = [p.get_text(" ", strip=True) for p in card.find_all("p")]
    if len(ps) < 5:
        return None
    pais = ps[0]
    ciudad = ps[1]
    fecha = ps[2]
    hora = ps[3]
    # ps[4] = orquesta + sede (separados por <br>)
    fuerte = card.find("strong")
    orquesta = fuerte.get_text(" ", strip=True) if fuerte else ""
    # sede: texto del quarto <p> sin el strong
    p_venue = ps[4]
    sede = p_venue.replace(orquesta, "").strip() if orquesta else p_venue

    enlace = ""
    a = card.find("a", href=True)
    if a:
        enlace = urljoin(html_base, a["href"])

    estado = ESTADO_ENVENTA
    fecha_venta = ""
    if seccion == "soldout" or card.find(class_="btn-soldout"):
        estado = ESTADO_AGOTADO
    else:
        nsy = card.find(class_="btn-notstartedyet")
        if nsy:
            estado = ESTADO_PROXIMAMENTE
            fecha_venta = " ".join(nsy.get_text(" ", strip=True).replace("on sale", "").split())

    return {
        "pais": pais,
        "ciudad": ciudad,
        "fecha": fecha,
        "hora": hora,
        "orquesta": orquesta,
        "sede": sede,
        "estado": estado,
        "fecha_venta": fecha_venta,
        "enlace": enlace,
        "seccion": seccion,
    }


def scrape(url=URL, reintentos=3):
    """Devuelve lista de dicts (conciertos). Lanza excepción si falla la descarga."""
    resp = None
    for intento in range(reintentos):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            break
        except (requests.ConnectionError, requests.Timeout):
            if intento == reintentos - 1:
                raise
            time.sleep(2)
    soup = BeautifulSoup(resp.text, "lxml")

    conciertos = []
    for section in soup.find_all("section", class_="news-list"):
        # la seccion "sold-out" es la que precede a un h2 "Sold-Out Concerts"
        seccion = "tickets"
        prev_h2 = section.find_parent("section")
        if prev_h2:
            h2 = prev_h2.find("h2")
            if h2 and "sold-out" in h2.get_text(" ", strip=True).lower():
                seccion = "soldout"
        for card in section.select("div.articletype-0"):
            datos = _parse_card(card, seccion, url)
            if datos:
                conciertos.append(datos)
    return conciertos


def clave(c):
    """Identificador único estable de un concierto."""
    return f"{c['pais']}|{c['ciudad']}|{c['fecha']}|{c['hora']}|{c['sede']}"


MESES = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
         "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}


def orden_fecha(c):
    """Clave de ordenación cronológica para fechas tipo '3 APR 2027' o 'OCT 2027'."""
    partes = c["fecha"].split()
    try:
        if len(partes) == 3:
            return (int(partes[2]), MESES.get(partes[1].upper(), 1), int(partes[0]))
        if len(partes) == 2:
            return (int(partes[1]), MESES.get(partes[0].upper(), 1), 1)
    except ValueError:
        pass
    return (9999, 1, 1)


if __name__ == "__main__":
    cs = scrape()
    print(f"Total conciertos: {len(cs)}")
    ciudades = sorted({(c["pais"], c["ciudad"]) for c in cs})
    print(f"Total ciudades: {len(ciudades)}")
    for c in cs:
        print(f"  [{c['estado']:12}] {c['pais']:6} {c['ciudad']:20} {c['fecha']:14} {c['hora']:8} {c['sede']}")
