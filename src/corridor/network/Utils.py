"""
Utils.py
========================


Descripción:
------------
Constantes y utilidades del módulo network: ubicación de los archivos
de cada corredor, el área descargada de OpenStreetMap y los radios con
que se agrupan los postes del inventario de semáforos y se emparejan
con los cruces de la red de SUMO.


Consideraciones:
------------
- Los radios se eligieron con el inventario 2021 alrededor de CU BUAP:
  los postes de una misma intersección quedan a menos de 35 m entre sí,
  y las intersecciones vecinas más cercanas (entrada a Derecho y 22 Sur
  en San Claudio) están a unos 60 m, con calles distintas
- El área de cada corredor es la que se eligió en osmWebWizard, no el
  límite de la red: la red se extiende más allá porque netconvert
  conserva completas las calles que cruzan el borde


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Nombres de la configuración y la red base
zxxz6       26/09/2026      Creación


"""

import unicodedata

from corridor.common.Utils import DATA_DIR, NETWORKS_DIR

# --------------------------------------------------------------------------
# Archivos
# --------------------------------------------------------------------------

SIGNAL_INVENTORY_PATH = DATA_DIR / "signals" / "SignalInventory2021.geojson"

NETCCFG_FILE_NAME = "Corridor.netccfg"
NET_FILE_NAME = "generated/Corridor.net.xml.gz"
BASE_NET_FILE_NAME = "Base.net.xml.gz"
SIGNALS_FILE_NAME = "Signals.csv"

DEFAULT_CORRIDOR = "puebla"

# --------------------------------------------------------------------------
# Área de cada corredor: (lon_min, lat_min, lon_max, lat_max), WGS84
# --------------------------------------------------------------------------

CORRIDOR_BBOX = {
    "puebla": (
        -98.21086835861207,
        18.982199018262875,
        -98.19042563438417,
        19.01391453950671,
    ),
}

# --------------------------------------------------------------------------
# Agrupamiento y emparejamiento del inventario
# --------------------------------------------------------------------------

# Dos postes pertenecen a la misma intersección si están a esta
# distancia o menos.
POLE_LINK_RADIUS_M = 35.0

# Radio mayor para postes que nombran exactamente las mismas calles:
# cubre intersecciones amplias como 14 Sur y San Claudio.
SAME_STREETS_LINK_RADIUS_M = 80.0

# Distancia máxima entre el centro de una intersección del inventario y
# el cruce de SUMO con el que se empareja.
MATCH_RADIUS_M = 30.0

# Nodos de SUMO que no son cruces reales.
IGNORED_NODE_TYPES = frozenset({"dead_end", "internal"})

# Campos del GeoJSON 2021.
STREET_FIELDS = ("CALLE_1", "CALLE_2", "CALLE_3")
PEDESTRIAN_HEADS_FIELD = "CAB_PEATON"

# Columnas de Signals.csv. node_id va primero porque BuildNetwork.sh lo
# lee con cut.
SIGNALS_COLUMNS = (
    "node_id",
    "status",
    "crossing",
    "lat",
    "lon",
    "poles",
    "pedestrian_heads",
    "match_distance_m",
)

# Valores de la columna status.
STATUS_ALREADY_IN_OSM = "already_in_osm"
STATUS_ADDED = "added"
STATUS_UNMATCHED = "unmatched"


# --------------------------------------------------------------------------
# Funciones
# --------------------------------------------------------------------------


def corridor_dir(corridor):
    """
    Devuelve el directorio de un corredor dentro de networks/.

    Entradas:
    -------
    corridor: Nombre del corredor, p. ej. 'puebla'

    Retorna:
    -------
    Path: Ruta al directorio networks/<corridor>

    """
    return NETWORKS_DIR / corridor


def normalize_street(name):
    """
    Normaliza un nombre de calle para comparar entre registros.
    Quita acentos, espacios sobrantes y pasa a mayúsculas; el inventario
    mezcla "RIO PAPAGAYO" con "RÍO PAPAGAYO" según el levantamiento.

    Entradas:
    -------
    name: Nombre de calle tal como viene en el inventario, o None

    Retorna:
    -------
    str: Nombre normalizado; cadena vacía si no había nombre

    """
    ascii_name = (
        unicodedata.normalize("NFKD", name or "")
        .encode("ascii", "ignore")
        .decode()
    )
    return " ".join(ascii_name.upper().split())


############################## FIN DE UTILS.PY #################################
################################################################################
