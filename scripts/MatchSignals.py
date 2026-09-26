"""
MatchSignals.py
========================


Descripción:
------------
Punto de entrada que empareja el inventario de semáforos con la red de
un corredor y escribe networks/<corredor>/Signals.csv. BuildNetwork.sh
lee ese archivo para declarar los semáforos en netconvert.


Consideraciones:
------------
- Uso: python scripts/MatchSignals.py [--corridor puebla]
- Solo hace falta volver a correrlo si cambia el inventario o el
  extracto de OSM; Signals.csv está versionado
- No necesita la red construida: arma su propia red base temporal.
  Después de correrlo, reconstruye con scripts/BuildNetwork.sh para
  que los semáforos aparezcan
- Con --check solo verifica la red construida; BuildNetwork.sh lo
  corre al final y se detiene si falta algún semáforo
- Sin lógica: todo vive en corridor.network.SignalInventory


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Opción --check para verificar la red
zxxz6       26/09/2026      Creación


"""

import argparse
import sys
from collections import Counter

from corridor.network.SignalInventory import (
    match_inventory,
    missing_signals,
    write_signals,
)
from corridor.network.Utils import (
    DEFAULT_CORRIDOR,
    SIGNAL_INVENTORY_PATH,
    SIGNALS_FILE_NAME,
    STATUS_UNMATCHED,
    corridor_dir,
)


def main():
    """
    Lee los argumentos, empareja el inventario y escribe Signals.csv.
    Imprime un resumen por estado y las intersecciones sin emparejar.

    Entradas:
    -------
    None: Los argumentos llegan por línea de comandos

    Retorna:
    -------
    None

    """
    parser = argparse.ArgumentParser(
        description="Empareja el inventario de semáforos con la red."
    )
    parser.add_argument("--corridor", default=DEFAULT_CORRIDOR)
    parser.add_argument("--inventory", default=str(SIGNAL_INVENTORY_PATH))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Solo verifica que la red construida tenga todos los "
        "semáforos de Signals.csv; sale con 1 si falta alguno.",
    )
    args = parser.parse_args()

    if args.check:
        missing = missing_signals(args.corridor)
        if missing:
            print(
                f"ERROR: {len(missing)} nodos de Signals.csv no tienen "
                "semáforo en la red. Revisa que SUMO sea la versión fijada "
                "en pyproject.toml: " + ", ".join(missing),
                file=sys.stderr,
            )
            sys.exit(1)
        print("Verificación: todos los semáforos de Signals.csv están.")
        return

    matches = match_inventory(args.corridor, args.inventory)
    output = corridor_dir(args.corridor) / SIGNALS_FILE_NAME
    write_signals(matches, output)

    counts = Counter(match.status for match in matches)
    print(f"Intersecciones del inventario: {len(matches)}")
    for status, count in sorted(counts.items()):
        print(f"  {status}: {count}")
    for match in matches:
        if match.status == STATUS_UNMATCHED:
            print(
                f"  Sin cruce a menos del radio: {match.crossing} "
                f"({match.lat}, {match.lon})"
            )
    print(f"Escrito {output}")


if __name__ == "__main__":
    main()


########################### FIN DE MATCHSIGNALS.PY #############################
################################################################################
