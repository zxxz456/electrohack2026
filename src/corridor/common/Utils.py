"""
Utils.py
========================


Descripción:
------------
Constantes y utilidades compartidas por todos los módulos del paquete
corridor: rutas del repositorio, límites de tiempos del semáforo,
parámetros peatonales y semillas. Aquí también vivirán las unidades
cuando los módulos que las usan existan.


Consideraciones:
------------
- Las rutas se calculan desde la ubicación de este archivo, así
  funcionan igual desde scripts, pruebas o notebooks, sin depender del
  directorio de trabajo
- Nada en este archivo importa de otros módulos del paquete: common es
  la raíz del grafo de dependencias
- Los límites de tiempos aplican a todos los controladores por igual,
  incluido el de tiempo fijo; los hace cumplir la capa de seguridad de
  env/, nunca el controlador
- El ámbar más el todo rojo dura exactamente un intervalo de decisión:
  al avanzar de etapa, el agente vuelve a decidir con la etapa nueva ya
  en verde
- PED_START_S sigue al MUTCD 2009 (sección 4E.06), que pide al menos
  7 s de paso peatonal. PENDIENTE: contrastarlo con el manual mexicano
  de dispositivos para el control del tránsito
- PED_SPEED_MPS es conservadora a propósito: el MUTCD usa 1.07 m/s, y
  1.0 m/s cubre mejor a personas mayores
- Semillas: una corrida usa la misma semilla para generar su demanda y
  para SUMO. Las de entrenamiento van de 0 a TRAIN_SEED_LIMIT - 1 y las
  de evaluación empiezan en TRAIN_SEED_LIMIT, así nunca se traslapan


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Límites de tiempos, peatones, semillas y YAML
zxxz6       26/09/2026      Creación, rutas del repositorio


"""

from pathlib import Path

import yaml

# --------------------------------------------------------------------------
# Rutas del repositorio
# --------------------------------------------------------------------------

# src/corridor/common/Utils.py -> la raíz está tres niveles arriba.
REPO_DIR = Path(__file__).resolve().parents[3]

NETWORKS_DIR = REPO_DIR / "networks"
CONFIGS_DIR = REPO_DIR / "configs"
DATA_DIR = REPO_DIR / "data"
RESULTS_DIR = REPO_DIR / "results"

# --------------------------------------------------------------------------
# Tiempos del semáforo, en segundos
# --------------------------------------------------------------------------

DECISION_INTERVAL_S = 5
MIN_GREEN_S = 10
AMBER_S = 3
ALL_RED_S = 2
MAX_GREEN_S = 60

# --------------------------------------------------------------------------
# Peatones
# --------------------------------------------------------------------------

# Paso peatonal: tiempo en verde al inicio de la etapa para empezar a
# cruzar. Después viene el despeje, en rojo para peatones.
PED_START_S = 7
PED_SPEED_MPS = 1.0

# --------------------------------------------------------------------------
# Semillas
# --------------------------------------------------------------------------

TRAIN_SEED_LIMIT = 1000
EVAL_SEEDS = tuple(range(TRAIN_SEED_LIMIT, TRAIN_SEED_LIMIT + 5))

# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------


def load_yaml(path):
    """
    Lee un archivo YAML de configuración.

    Entradas:
    -------
    path: Ruta al archivo

    Retorna:
    -------
    object: El contenido del archivo, normalmente un dict

    """
    with open(path, encoding="utf-8") as handle:
        return yaml.safe_load(handle)


############################## FIN DE UTILS.PY #################################
################################################################################
