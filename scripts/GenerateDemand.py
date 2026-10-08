"""
GenerateDemand.py
========================


Descripción:
------------
Punto de entrada que genera la demanda de uno o varios escenarios, una
vez por semilla. La salida va a networks/<red>/generated/demand/, que no
se versiona: cada integrante la regenera y, con la misma semilla,
obtiene exactamente la misma demanda.


Consideraciones:
------------
- Uso: python scripts/GenerateDemand.py [--scenario PeakHour ...]
  [--seeds 1000 1001 ...]. Sin --scenario genera todos los de
  configs/scenarios/; sin --seeds usa las semillas de evaluación
- Requiere la red construida (scripts/BuildNetwork.sh)
- Sin lógica: todo vive en corridor.network.Demand


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

import argparse

from corridor.common.Utils import EVAL_SEEDS
from corridor.network.Demand import generate_demand
from corridor.network.Utils import SCENARIOS_DIR


def main():
    """
    Lee los argumentos y genera la demanda de cada escenario y semilla.
    Imprime cuántos viajes quedaron en cada archivo.

    Entradas:
    -------
    None: Los argumentos llegan por línea de comandos

    Retorna:
    -------
    None

    """
    scenarios = sorted(path.stem for path in SCENARIOS_DIR.glob("*.yaml"))
    parser = argparse.ArgumentParser(
        description="Genera la demanda de los escenarios."
    )
    parser.add_argument("--scenario", nargs="+", default=scenarios)
    parser.add_argument("--seeds", nargs="+", type=int, default=EVAL_SEEDS)
    args = parser.parse_args()

    for scenario in args.scenario:
        for seed in args.seeds:
            print(f"{scenario}, semilla {seed}:")
            for path in generate_demand(scenario, seed):
                trips = path.read_text(encoding="utf-8").count(
                    "<person " if "Pedestrian" in path.name else "<vehicle "
                )
                print(f"  {path.name}: {trips} viajes")


if __name__ == "__main__":
    main()


######################### FIN DE GENERATEDEMAND.PY #############################
################################################################################
