"""
BuildStudyArea.py
========================


Descripción:
------------
Punto de entrada que recorta la red completa a la zona de estudio de
cada corredor que la declara. BuildNetwork.sh lo corre al final, así la
zona siempre corresponde a la red recién construida.


Consideraciones:
------------
- Uso: python scripts/BuildStudyArea.py [--network puebla]. Recorta
  todos los corredores de configs/corridors/ sobre esa red que declaran
  study_area_m
- Se detiene con error si el recorte cambia algún semáforo del corredor
- Sin lógica: todo vive en corridor.network.StudyArea


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

from corridor.network.CorridorSpec import load_corridor_spec
from corridor.network.StudyArea import build_study_area
from corridor.network.Utils import CORRIDORS_DIR, DEFAULT_CORRIDOR


def main():
    """
    Recorta la zona de estudio de cada corredor de una red.

    Entradas:
    -------
    None: Los argumentos llegan por línea de comandos

    Retorna:
    -------
    None

    """
    parser = argparse.ArgumentParser(
        description="Recorta las zonas de estudio de los corredores."
    )
    parser.add_argument("--network", default=DEFAULT_CORRIDOR)
    args = parser.parse_args()

    for path in sorted(CORRIDORS_DIR.glob("*.yaml")):
        spec = load_corridor_spec(path.stem)
        if spec["network"] != args.network:
            continue
        if spec.get("study_area_m") is None:
            continue
        area_path = build_study_area(path.stem)
        print(f"Zona de estudio de {path.stem}: {area_path}")


if __name__ == "__main__":
    main()


######################## FIN DE BUILDSTUDYAREA.PY ##############################
################################################################################
