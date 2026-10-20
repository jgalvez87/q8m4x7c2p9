"""
Sync cloud: scrapea zelda.gameconcerts.com y actualiza estado.json si cambia.
Ejecutado por GitHub Actions cada 5 min.
Mantiene historial de cambios (para mostrar "ultimos cambios" en la web).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scraper import scrape, clave, ESTADO_AGOTADO

ESTADO = Path(__file__).parent / "estado.json"
MIN_CONCIERTOS = 5
MAX_HISTORIAL = 20


def cargar():
    if ESTADO.exists():
        try:
            return json.loads(ESTADO.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def diff(antiguos, nuevos):
    eventos = []
    ciudades_antes = {a["ciudad"] for a in antiguos.values()}
    for k, c in nuevos.items():
        if k not in antiguos:
            tipo = "nueva_ciudad" if c["ciudad"] not in ciudades_antes else "nuevo_concierto"
            eventos.append(f"[{tipo}] {c['ciudad']} ({c['pais']}) {c['fecha']}")
        elif antiguos[k]["estado"] != c["estado"]:
            if c["estado"] == ESTADO_AGOTADO:
                eventos.append(f"[agotado] {c['ciudad']} ({c['pais']}) {c['fecha']} {c['hora']}")
            elif antiguos[k]["estado"] == ESTADO_AGOTADO:
                eventos.append(f"[liberado] {c['ciudad']} ({c['pais']}) {c['fecha']} {c['hora']}")
            else:
                eventos.append(f"[estado] {c['ciudad']} ({c['pais']}) {c['fecha']} -> {c['estado']}")
    for k, a in antiguos.items():
        if k not in nuevos:
            eventos.append(f"[retirado] {a['ciudad']} ({a['pais']}) {a['fecha']}")
    return eventos


def main():
    prev = cargar()
    viejos = prev.get("conciertos", {})
    historial = prev.get("historial", [])
    try:
        lista = scrape()
    except Exception as e:
        print(f"SCRAPE_ERROR: {type(e).__name__}: {e}")
        sys.exit(1)  # no tocar estado ante fallo
    if len(lista) < MIN_CONCIERTOS:
        print(f"PARSE_BAJO: solo {len(lista)} conciertos - se ignora")
        sys.exit(1)

    nuevos = {clave(c): c for c in lista}
    eventos = diff(viejos, nuevos)
    for e in eventos:
        print(f"EVENTO {e}")

    ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    if eventos:
        historial = [{"cuando": ahora, "eventos": eventos}] + historial
        historial = historial[:MAX_HISTORIAL]

    estado = {
        "actualizado": ahora,
        "total": len(nuevos),
        "ciudades": len({c["ciudad"] for c in nuevos.values()}),
        "historial": historial,
        "conciertos": nuevos,
    }
    ESTADO.write_text(json.dumps(estado, ensure_ascii=False, indent=1), encoding="utf-8")
    # heartbeat: se commitea SIEMPRE para que 'actualizado' refleje el ultimo scrape ok
    print(f"GUARDADO: {len(nuevos)} conciertos, {len(eventos)} cambios")


if __name__ == "__main__":
    main()
