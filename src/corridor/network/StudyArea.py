"""
StudyArea.py
========================


Descripción:
------------
Recorta la red completa a la zona de estudio de un corredor: los tramos
a menos de study_area_m de sus semáforos. Los experimentos del corredor
corren sobre esa red recortada; los autos entran y salen por los bordes
del recorte.


Consideraciones:
------------
- Por qué recortar: en la red completa, los autos que salen de San
  Claudio hacia Circunvalación saturan esos cruces y la cola regresa
  hasta el corredor. Sin aforos no hay forma de calibrar cuánto tráfico
  va hacia allá, y ese bloqueo contaminaría cualquier comparación entre
  controladores del corredor
- El recorte es el casco convexo de círculos de radio study_area_m
  alrededor de cada semáforo, en el orden del corredor. En un corredor
  casi recto es casi el mismo que un margen alrededor del eje
- netconvert conserva completos los tramos que cruzan el borde, así que
  los accesos de los semáforos quedan enteros
- Las coordenadas no se normalizan: un punto de la zona tiene las mismas
  coordenadas que en la red completa
- Al terminar se verifica que cada semáforo del corredor tenga en la
  zona los mismos enlaces y el mismo programa que en la red completa.
  Las etapas declaradas a mano (Stages.yaml) dependen de los índices de
  enlace
- Un corredor sin study_area_m usa la red completa


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

import math
import subprocess

from corridor.common.Utils import NETWORKS_DIR
from corridor.network.CorridorSpec import (
    corridor_axis,
    load_corridor_spec,
    resolve_signals,
)
from corridor.network.Utils import AREAS_DIR_NAME, NET_FILE_NAME

# Puntos por círculo al aproximar el margen alrededor de cada semáforo.
CIRCLE_POINTS = 16

# --------------------------------------------------------------------------
# Geometría
# --------------------------------------------------------------------------


def convex_hull(points):
    """
    Casco convexo de un conjunto de puntos, por cadena monótona.

    Entradas:
    -------
    points: Lista de (x_m, y_m)

    Retorna:
    -------
    list: Vértices del casco en sentido antihorario, sin repetir el
        primero

    """
    unique = sorted(set(points))
    if len(unique) < 3:
        return unique

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower, upper = [], []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def study_area_polygon(axis, margin_m):
    """
    Polígono de la zona de estudio: casco convexo de círculos de radio
    margin_m alrededor de cada punto del eje.

    Entradas:
    -------
    axis: Posiciones de los semáforos del corredor, (x_m, y_m)
    margin_m: Radio del margen

    Retorna:
    -------
    list: Vértices del polígono, (x_m, y_m)

    """
    points = [
        (
            x + margin_m * math.cos(2 * math.pi * k / CIRCLE_POINTS),
            y + margin_m * math.sin(2 * math.pi * k / CIRCLE_POINTS),
        )
        for x, y in axis
        for k in range(CIRCLE_POINTS)
    ]
    return convex_hull(points)


# --------------------------------------------------------------------------
# Red de la zona
# --------------------------------------------------------------------------


def corridor_net_path(corridor_name):
    """
    Red sobre la que corren los experimentos de un corredor: la zona de
    estudio si el corredor la declara, la red completa si no.

    Entradas:
    -------
    corridor_name: Nombre del archivo del corredor, p. ej. 'SanClaudio'

    Retorna:
    -------
    Path: Archivo .net.xml.gz

    """
    spec = load_corridor_spec(corridor_name)
    network_dir = NETWORKS_DIR / spec["network"]
    if spec.get("study_area_m") is None:
        return network_dir / NET_FILE_NAME
    return network_dir / AREAS_DIR_NAME / f"{corridor_name}.net.xml.gz"


def _signal_signature(net, tls_id):
    """
    Enlaces y programa de un semáforo, para comparar dos redes.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms
    tls_id: ID del semáforo

    Retorna:
    -------
    tuple: (conjunto de enlaces, lista de estados del programa)

    """
    tls = net.getTLS(tls_id)
    links = {
        (in_lane.getID(), out_lane.getID(), link)
        for in_lane, out_lane, link in tls.getConnections()
    }
    program = next(iter(tls.getPrograms().values()))
    return links, [phase.state for phase in program.getPhases()]


def build_study_area(corridor_name):
    """
    Recorta la red completa a la zona de estudio de un corredor y
    verifica que sus semáforos no cambien.

    Entradas:
    -------
    corridor_name: Nombre del archivo del corredor

    Retorna:
    -------
    Path: Red de la zona. Lanza ValueError si el corredor no declara
        study_area_m o si algún semáforo cambió con el recorte

    """
    import sumolib

    spec = load_corridor_spec(corridor_name)
    if spec.get("study_area_m") is None:
        raise ValueError(f"{corridor_name} no declara study_area_m")
    full_path = NETWORKS_DIR / spec["network"] / NET_FILE_NAME
    area_path = corridor_net_path(corridor_name)
    area_path.parent.mkdir(parents=True, exist_ok=True)

    read_options = {
        "withPrograms": True,
        "withInternal": True,
        "withPedestrianConnections": True,
    }
    full = sumolib.net.readNet(str(full_path), **read_options)
    signals = resolve_signals(full, spec)
    polygon = study_area_polygon(
        corridor_axis(full, signals), float(spec["study_area_m"])
    )
    boundary = ",".join(
        f"{x:.1f},{y:.1f}" for x, y in polygon + [polygon[0]]
    )
    subprocess.run(
        [
            sumolib.checkBinary("netconvert"),
            "-s", str(full_path),
            "--keep-edges.in-boundary", boundary,
            "--remove-edges.isolated",
            "--keep-edges.components", "1",
            "--offset.disable-normalization",
            "--no-warnings",
            "-o", str(area_path),
        ],
        check=True,
    )

    area = sumolib.net.readNet(str(area_path), **read_options)
    for signal in signals:
        if _signal_signature(full, signal.tls_id) != _signal_signature(
            area, signal.tls_id
        ):
            raise ValueError(
                f"{signal.name}: el recorte cambió los enlaces o el "
                "programa del semáforo"
            )
    return area_path


########################### FIN DE STUDYAREA.PY ################################
################################################################################
