"""
Utils.py
========================


Descripción:
------------
Constantes y utilidades compartidas por todos los módulos del paquete
corridor. Por ahora contiene las rutas del repositorio; aquí también
vivirán los límites de tiempos del semáforo, las unidades y las
semillas cuando los módulos que las usan existan.


Consideraciones:
------------
- Las rutas se calculan desde la ubicación de este archivo, así
  funcionan igual desde scripts, pruebas o notebooks, sin depender del
  directorio de trabajo
- Nada en este archivo importa de otros módulos del paquete: common es
  la raíz del grafo de dependencias


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Creación, rutas del repositorio


"""

from pathlib import Path

# --------------------------------------------------------------------------
# Rutas del repositorio
# --------------------------------------------------------------------------

# src/corridor/common/Utils.py -> la raíz está tres niveles arriba.
REPO_DIR = Path(__file__).resolve().parents[3]

NETWORKS_DIR = REPO_DIR / "networks"
DATA_DIR = REPO_DIR / "data"
RESULTS_DIR = REPO_DIR / "results"


############################## FIN DE UTILS.PY #################################
################################################################################
