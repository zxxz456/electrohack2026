"""
CorridorSpec.py
========================


Descripción:
------------
Lee qué semáforos controlan los agentes, a partir de un archivo de
configs/corridors/. El archivo nombra la red y una lista ordenada de
intersecciones; el orden define los vecinos de cada agente sobre el
corredor. También da la geometría del corredor: los nodos de cada
semáforo y el eje que los une.


Consideraciones:
------------
- Cada intersección se identifica por un nodo de la red y no por el ID
  del semáforo: los semáforos que netconvert une tienen IDs largos y
  generados (el de 14 Sur mide 85 caracteres), y los nodos no cambian
  al unir o separar semáforos
- Cambiar de corredor, o pasar a toda la red, es cambiar de archivo; el
  entorno no tiene ninguna intersección fija en el código


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación, con nodos y eje del corredor


"""

from dataclasses import dataclass

from corridor.common.Utils import load_yaml
from corridor.network.Utils import CORRIDORS_DIR

# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ControlledSignal:
    """
    Una intersección controlada por un agente.

    Atributos:
    -------
    name: Nombre legible, para logs y figuras
    node_id: Nodo de la red con el que se declaró en el archivo
    tls_id: ID del semáforo que controla ese nodo

    """

    name: str
    node_id: str
    tls_id: str


# --------------------------------------------------------------------------
# Lectura
# --------------------------------------------------------------------------


def load_corridor_spec(corridor_name):
    """
    Lee el archivo de un corredor.

    Entradas:
    -------
    corridor_name: Nombre del archivo sin extensión, p. ej. 'SanClaudio'

    Retorna:
    -------
    dict: Con 'network' (directorio en networks/), 'signals' (lista de
        dicts con 'name' y 'node') y, opcional, 'study_area_m'

    """
    return load_yaml(CORRIDORS_DIR / f"{corridor_name}.yaml")


def tls_by_node(net):
    """
    Relaciona cada nodo semaforizado con el semáforo que lo controla.
    Un semáforo conjunto aparece una vez por cada uno de sus nodos.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms

    Retorna:
    -------
    dict: ID de nodo -> ID de semáforo

    """
    mapping = {}
    for tls in net.getTrafficLights():
        for in_lane, _, _ in tls.getConnections():
            edge = in_lane.getEdge()
            if edge.getFunction() == "":
                mapping[edge.getToNode().getID()] = tls.getID()
    return mapping


def resolve_signals(net, spec):
    """
    Encuentra el semáforo de cada intersección del corredor.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms
    spec: Contenido del archivo del corredor, de load_corridor_spec

    Retorna:
    -------
    list: ControlledSignal en el orden del archivo. Lanza ValueError si
        un nodo no tiene semáforo o si dos entradas caen en el mismo

    """
    mapping = tls_by_node(net)
    signals = []
    for entry in spec["signals"]:
        node_id = str(entry["node"])
        if node_id not in mapping:
            raise ValueError(
                f"{entry['name']}: el nodo {node_id} no tiene semáforo "
                "en la red. Revisa ManualSignals.csv y reconstruye"
            )
        signals.append(
            ControlledSignal(
                name=entry["name"],
                node_id=node_id,
                tls_id=mapping[node_id],
            )
        )
    tls_ids = [signal.tls_id for signal in signals]
    if len(set(tls_ids)) != len(tls_ids):
        raise ValueError(
            "Dos intersecciones del corredor caen en el mismo semáforo: "
            + ", ".join(tls_ids)
        )
    return signals


# --------------------------------------------------------------------------
# Geometría
# --------------------------------------------------------------------------


def tls_nodes(tls):
    """
    Nodos que controla un semáforo, sacados de sus conexiones.

    Entradas:
    -------
    tls: Semáforo de sumolib

    Retorna:
    -------
    list: Nodos de sumolib, sin repetir

    """
    nodes = {}
    for in_lane, _, _ in tls.getConnections():
        edge = in_lane.getEdge()
        if edge.getFunction() == "":
            node = edge.getToNode()
            nodes[node.getID()] = node
    return list(nodes.values())


def _center(nodes):
    """
    Centro de un grupo de nodos.

    Entradas:
    -------
    nodes: Nodos de sumolib

    Retorna:
    -------
    tuple: (x_m, y_m)

    """
    xs, ys = zip(*(node.getCoord() for node in nodes), strict=True)
    return sum(xs) / len(xs), sum(ys) / len(ys)


def corridor_axis(net, signals):
    """
    Posiciones de los semáforos del corredor, en su orden.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms
    signals: ControlledSignal del corredor, en orden

    Retorna:
    -------
    list: (x_m, y_m) del centro de cada semáforo

    """
    return [
        _center(tls_nodes(net.getTLS(signal.tls_id))) for signal in signals
    ]


########################### FIN DE CORRIDORSPEC.PY #############################
################################################################################
