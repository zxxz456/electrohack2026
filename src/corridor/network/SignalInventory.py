"""
SignalInventory.py
========================


Descripción:
------------
Conecta el inventario de semáforos del municipio de Puebla con la red
de SUMO. Agrupa los postes del inventario en intersecciones, empareja
cada intersección con el cruce más cercano de la red y escribe la lista
de nodos semaforizados que BuildNetwork.sh pasa a netconvert con
tls.set. OpenStreetMap casi no tiene semáforos mapeados en Puebla; sin
este paso la línea base de tiempo fijo no representaría la ciudad.


Consideraciones:
------------
- Cada registro del inventario es un poste, no una intersección. El
  agrupamiento es por componentes conexas: dos postes se ligan si están
  a POLE_LINK_RADIUS_M o menos, o a SAME_STREETS_LINK_RADIUS_M o menos
  cuando nombran las mismas calles
- El emparejamiento prefiere un cruce que ya tenga semáforo en OSM
  dentro del radio; si no hay, toma el cruce real más cercano
- Fuera del área elegida solo entran cruces con al menos dos calles que
  llegan; en la orilla la calle transversal suele faltar
- Las funciones de agrupamiento y emparejamiento reciben datos simples
  (Pole, Junction) y no la red de SUMO, para poder probarlas sin
  construir una red
- El estado already_in_osm se calcula contra una red base construida
  sin los semáforos del inventario. Contra la red final todo saldría
  como ya semaforizado y BuildNetwork.sh dejaría de declararlos
- Los IDs de nodo no cambian al agregar semáforos con tls.set, así que
  los de la red base sirven para la red final


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Red base, verificación y cruces fuera del área
zxxz6       26/09/2026      Creación


"""

import csv
import json
import math
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path

from corridor.network.Utils import (
    BASE_NET_FILE_NAME,
    CORRIDOR_BBOX,
    IGNORED_NODE_TYPES,
    MATCH_RADIUS_M,
    MIN_APPROACH_STREETS,
    NET_FILE_NAME,
    NETCCFG_FILE_NAME,
    PEDESTRIAN_HEADS_FIELD,
    POLE_LINK_RADIUS_M,
    SAME_STREETS_LINK_RADIUS_M,
    SIGNAL_INVENTORY_PATH,
    SIGNALS_COLUMNS,
    SIGNALS_FILE_NAME,
    STATUS_ADDED,
    STATUS_ALREADY_IN_OSM,
    STATUS_UNMATCHED,
    STREET_FIELDS,
    corridor_dir,
    normalize_street,
)

# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Pole:
    """
    Un poste del inventario, ya proyectado a coordenadas de la red.

    Atributos:
    -------
    x_m, y_m: Posición en el sistema de coordenadas de la red, metros
    streets: Nombres normalizados de las calles del cruce
    pedestrian_heads: Cabezas peatonales montadas en el poste

    """

    x_m: float
    y_m: float
    streets: frozenset
    pedestrian_heads: int


@dataclass(frozen=True)
class Junction:
    """
    Un cruce real de la red de SUMO, candidato a emparejarse.

    Atributos:
    -------
    node_id: ID del nodo en la red
    x_m, y_m: Posición en el sistema de coordenadas de la red, metros
    has_signal: True si ya tiene semáforo en la red construida desde OSM
    approach_streets: Calles distintas por las que llegan autos al cruce

    """

    node_id: str
    x_m: float
    y_m: float
    has_signal: bool
    approach_streets: int = MIN_APPROACH_STREETS


@dataclass(frozen=True)
class SignalMatch:
    """
    Una intersección del inventario y el cruce de SUMO que le toca.

    Atributos:
    -------
    node_id: ID del nodo emparejado; vacío si no hubo cruce en el radio
    status: STATUS_ALREADY_IN_OSM, STATUS_ADDED o STATUS_UNMATCHED
    crossing: Las dos calles más nombradas por los postes del grupo
    lat, lon: Centro del grupo de postes, WGS84
    poles: Número de postes del grupo
    pedestrian_heads: Cabezas peatonales sumadas del grupo
    match_distance_m: Distancia del centro del grupo al nodo emparejado
    inside_area: True si el grupo está dentro del área elegida en OSM

    """

    node_id: str
    status: str
    crossing: str
    lat: float
    lon: float
    poles: int
    pedestrian_heads: int
    match_distance_m: float
    inside_area: bool = True


# --------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------


def load_poles(inventory_path, bbox, to_xy):
    """
    Lee los postes del inventario GeoJSON que caen dentro de un área.

    Entradas:
    -------
    inventory_path: Ruta al GeoJSON del inventario 2021
    bbox: (lon_min, lat_min, lon_max, lat_max) del corredor, WGS84
    to_xy: Función (lon, lat) -> (x_m, y_m) de la red

    Retorna:
    -------
    list: Postes dentro del área, como Pole

    """
    with open(inventory_path, encoding="utf-8") as handle:
        features = json.load(handle)["features"]

    lon_min, lat_min, lon_max, lat_max = bbox
    poles = []
    for feature in features:
        lon, lat = feature["geometry"]["coordinates"]
        if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
            continue
        props = feature["properties"]
        streets = frozenset(
            normalize_street(props[field])
            for field in STREET_FIELDS
            if props.get(field)
        )
        x_m, y_m = to_xy(lon, lat)
        poles.append(
            Pole(
                x_m=x_m,
                y_m=y_m,
                streets=streets,
                pedestrian_heads=int(props.get(PEDESTRIAN_HEADS_FIELD) or 0),
            )
        )
    return poles


def junctions_from_net(net):
    """
    Extrae de una red de sumolib los cruces candidatos a emparejarse.
    Descarta extremos sin salida y nodos internos. Marca como
    semaforizados los nodos de tipo traffic_light y los que controla un
    semáforo conjunto, cuyo tipo no siempre lo refleja. Cuenta las calles
    distintas por las que llegan autos; una calle sin nombre cuenta por
    su ID de tramo.

    Entradas:
    -------
    net: Red cargada con sumolib.net.readNet

    Retorna:
    -------
    list: Cruces de la red, como Junction

    """
    controlled = set()
    for tls in net.getTrafficLights():
        for incoming, _outgoing, _index in tls.getConnections():
            controlled.add(incoming.getEdge().getToNode().getID())

    junctions = []
    for node in net.getNodes():
        if node.getType() in IGNORED_NODE_TYPES:
            continue
        x_m, y_m = node.getCoord()
        has_signal = (
            node.getType().startswith("traffic_light")
            or node.getID() in controlled
        )
        streets = {
            edge.getName() or edge.getID()
            for edge in node.getIncoming()
            if edge.allows("passenger")
        }
        junctions.append(
            Junction(node.getID(), x_m, y_m, has_signal, len(streets))
        )
    return junctions


# --------------------------------------------------------------------------
# Agrupamiento
# --------------------------------------------------------------------------


def _linked(first, second):
    """
    Decide si dos postes pertenecen a la misma intersección.

    Entradas:
    -------
    first, second: Postes a comparar

    Retorna:
    -------
    bool: True si deben quedar en el mismo grupo

    """
    distance_m = math.hypot(first.x_m - second.x_m, first.y_m - second.y_m)
    if distance_m <= POLE_LINK_RADIUS_M:
        return True
    return (
        distance_m <= SAME_STREETS_LINK_RADIUS_M
        and first.streets == second.streets
    )


def cluster_poles(poles):
    """
    Agrupa postes en intersecciones por componentes conexas.
    Usa union-find sobre todos los pares; con unos cientos de postes por
    corredor el costo cuadrático es despreciable.

    Entradas:
    -------
    poles: Lista de Pole

    Retorna:
    -------
    list: Lista de grupos; cada grupo es una lista de Pole

    """
    parent = list(range(len(poles)))

    def find(index):
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for i in range(len(poles)):
        for j in range(i + 1, len(poles)):
            if _linked(poles[i], poles[j]):
                parent[find(i)] = find(j)

    groups = {}
    for index, pole in enumerate(poles):
        groups.setdefault(find(index), []).append(pole)
    return list(groups.values())


# --------------------------------------------------------------------------
# Emparejamiento
# --------------------------------------------------------------------------


def _crossing_name(group):
    """
    Nombra un grupo con las dos calles que más postes mencionan.

    Entradas:
    -------
    group: Lista de Pole de una intersección

    Retorna:
    -------
    str: Nombre del cruce, p. ej. '14 SUR x SAN CLAUDIO'

    """
    counts = Counter(street for pole in group for street in pole.streets)
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:2]
    return " x ".join(street for street, _count in top)


def match_group(group, junctions, to_lonlat):
    """
    Empareja una intersección del inventario con un cruce de la red.
    Dentro de MATCH_RADIUS_M prefiere un cruce que ya tenga semáforo;
    si no hay, toma el cruce más cercano. Fuera del radio no empareja.

    Entradas:
    -------
    group: Lista de Pole de una intersección
    junctions: Lista de Junction de la red
    to_lonlat: Función (x_m, y_m) -> (lon, lat) de la red

    Retorna:
    -------
    SignalMatch: Resultado del emparejamiento

    """
    center_x = sum(pole.x_m for pole in group) / len(group)
    center_y = sum(pole.y_m for pole in group) / len(group)

    by_distance = sorted(
        (math.hypot(j.x_m - center_x, j.y_m - center_y), j)
        for j in junctions
    )
    in_radius = [
        (distance_m, junction)
        for distance_m, junction in by_distance
        if distance_m <= MATCH_RADIUS_M
    ]
    signalized = [item for item in in_radius if item[1].has_signal]

    if signalized:
        distance_m, junction = signalized[0]
        status = STATUS_ALREADY_IN_OSM
    elif in_radius:
        distance_m, junction = in_radius[0]
        status = STATUS_ADDED
    else:
        distance_m, junction = by_distance[0]
        status = STATUS_UNMATCHED

    lon, lat = to_lonlat(center_x, center_y)
    return SignalMatch(
        node_id="" if status == STATUS_UNMATCHED else junction.node_id,
        status=status,
        crossing=_crossing_name(group),
        lat=round(lat, 6),
        lon=round(lon, 6),
        poles=len(group),
        pedestrian_heads=sum(pole.pedestrian_heads for pole in group),
        match_distance_m=round(distance_m, 1),
    )


def _inside(lon, lat, bbox):
    """
    Decide si un punto cae dentro de un rectángulo lon/lat.

    Entradas:
    -------
    lon, lat: Punto, WGS84
    bbox: (lon_min, lat_min, lon_max, lat_max)

    Retorna:
    -------
    bool: True si el punto está dentro o en el borde

    """
    lon_min, lat_min, lon_max, lat_max = bbox
    return lon_min <= lon <= lon_max and lat_min <= lat <= lat_max


def select_matches(groups, junctions, to_lonlat, bbox):
    """
    Empareja todos los grupos y decide cuáles entran a la red.
    Dentro del área elegida entran todos, incluso sin emparejar, para
    que se vean en el reporte. Fuera del área, en los tramos que la red
    conserva porque cruzan el borde, solo entran los emparejados con un
    cruce real: al menos MIN_APPROACH_STREETS calles que llegan. En la
    orilla la calle transversal suele quedar fuera de la descarga, y un
    semáforo sin tráfico con qué cruzarse solo agrega demora artificial.

    Entradas:
    -------
    groups: Lista de grupos de Pole
    junctions: Lista de Junction de la red base
    to_lonlat: Función (x_m, y_m) -> (lon, lat) de la red
    bbox: Área elegida en OSM, (lon_min, lat_min, lon_max, lat_max)

    Retorna:
    -------
    list: SignalMatch seleccionados, con inside_area marcado

    """
    by_id = {junction.node_id: junction for junction in junctions}
    selected = []
    for group in groups:
        match = match_group(group, junctions, to_lonlat)
        if _inside(match.lon, match.lat, bbox):
            selected.append(match)
            continue
        if match.status == STATUS_UNMATCHED:
            continue
        if by_id[match.node_id].approach_streets < MIN_APPROACH_STREETS:
            continue
        selected.append(replace(match, inside_area=False))
    return selected


def build_base_net(corridor, output_path):
    """
    Construye la red de un corredor solo con los semáforos de OSM.
    Es la referencia del emparejamiento: contra la red final, que ya
    trae los semáforos del inventario, todo aparecería como ya
    semaforizado y la siguiente construcción no los declararía.

    Entradas:
    -------
    corridor: Nombre del corredor, p. ej. 'puebla'
    output_path: Ruta del archivo de red a escribir

    Retorna:
    -------
    None

    """
    subprocess.run(
        [
            "netconvert",
            "-c",
            NETCCFG_FILE_NAME,
            "-o",
            str(output_path),
            "--no-warnings",
        ],
        cwd=corridor_dir(corridor),
        check=True,
        stdout=subprocess.DEVNULL,
    )


def match_inventory(corridor, inventory_path=SIGNAL_INVENTORY_PATH):
    """
    Empareja todo el inventario de un corredor con su red de SUMO.
    Construye en un directorio temporal la red base, sin semáforos del
    inventario, así el resultado no depende de lo que haya en
    generated/. Incluye los cruces reales de los tramos fuera del área
    elegida que la red conserva (ver select_matches).

    Entradas:
    -------
    corridor: Nombre del corredor, p. ej. 'puebla'
    inventory_path: Ruta al GeoJSON del inventario

    Retorna:
    -------
    list: SignalMatch ordenados de norte a sur

    """
    import sumolib

    with tempfile.TemporaryDirectory() as tmp:
        base_path = Path(tmp) / BASE_NET_FILE_NAME
        build_base_net(corridor, base_path)
        net = sumolib.net.readNet(str(base_path))

    def to_xy(lon, lat):
        return net.convertLonLat2XY(lon, lat)

    def to_lonlat(x_m, y_m):
        return net.convertXY2LonLat(x_m, y_m)

    # Los postes se leen en toda la extensión de la red, no solo en el
    # área elegida: la red conserva completas las calles que cruzan el
    # borde, y select_matches decide cuáles de esos cruces entran.
    x_min, y_min, x_max, y_max = net.getBoundary()
    net_extent = (*to_lonlat(x_min, y_min), *to_lonlat(x_max, y_max))

    poles = load_poles(inventory_path, net_extent, to_xy)
    matches = select_matches(
        cluster_poles(poles),
        junctions_from_net(net),
        to_lonlat,
        CORRIDOR_BBOX[corridor],
    )
    return sorted(matches, key=lambda match: (-match.lat, match.lon))


# --------------------------------------------------------------------------
# Lectura y escritura de Signals.csv
# --------------------------------------------------------------------------


def write_signals(matches, path):
    """
    Escribe la lista de intersecciones semaforizadas de un corredor.

    Entradas:
    -------
    matches: Lista de SignalMatch
    path: Ruta del CSV de salida

    Retorna:
    -------
    None

    """
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(SIGNALS_COLUMNS)
        for match in matches:
            writer.writerow(
                getattr(match, column) for column in SIGNALS_COLUMNS
            )


def missing_signals(corridor):
    """
    Lista los nodos de Signals.csv que no quedaron semaforizados en la
    red construida. netconvert solo advierte cuando tls.set nombra un
    nodo que no existe, así que sin esta verificación una versión
    distinta de SUMO podría perder semáforos sin que nadie lo note.

    Entradas:
    -------
    corridor: Nombre del corredor, p. ej. 'puebla'

    Retorna:
    -------
    list: IDs de nodo sin semáforo; vacía si la red está completa

    """
    import sumolib

    directory = corridor_dir(corridor)
    net = sumolib.net.readNet(str(directory / NET_FILE_NAME))
    signalized = {
        junction.node_id
        for junction in junctions_from_net(net)
        if junction.has_signal
    }
    expected = read_signal_node_ids(directory / SIGNALS_FILE_NAME)
    return [node_id for node_id in expected if node_id not in signalized]


def read_signal_node_ids(path):
    """
    Lee los IDs de nodo emparejados de un Signals.csv.
    Omite las intersecciones sin emparejar.

    Entradas:
    -------
    path: Ruta al CSV

    Retorna:
    -------
    list: IDs de nodo, en el orden del archivo

    """
    with open(path, newline="", encoding="utf-8") as handle:
        rows = csv.DictReader(handle)
        return [row["node_id"] for row in rows if row["node_id"]]


########################## FIN DE SIGNALINVENTORY.PY ###########################
################################################################################
