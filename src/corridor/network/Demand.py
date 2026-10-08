"""
Demand.py
========================


Descripción:
------------
Genera la demanda de un escenario con semilla fija: autos y peatones
para toda la duración del escenario. Tiene tres partes: tráfico de fondo
al azar en toda la red, tráfico del corredor ajustado a conteos por
acceso, y peatones concentrados alrededor del corredor. La salida son
tres archivos de rutas que SUMO carga juntos.


Consideraciones:
------------
- Tráfico del corredor: routeSampler, herramienta de SUMO, elige de un
  conjunto grande de rutas candidatas las que cumplen los conteos por
  acceso. Las candidatas son viajes al azar en toda la red más viajes
  dirigidos al corredor: de un tramo cercano, por un acceso, a otro
  tramo cercano. Los viajes al azar casi no usan algunos tramos del
  corredor y sin los dirigidos esos conteos quedan cortos
- Se descartan las candidatas con rodeos: más de MAX_DETOUR_RATIO veces
  la línea recta más DETOUR_SLACK_M. Sin vueltas en U, un viaje dirigido
  cuyo destino queda atrás rodea manzanas por calles locales y traba
  cruces sin semáforo
- Los conteos salen del escenario, por carril, según si el acceso es
  de la calle principal o de una lateral, y en la principal según su
  sentido. Los aforos medidos van en measured y reemplazan lo supuesto
  para ese tramo
- Un acceso es un tramo vehicular que entra a un semáforo del corredor
  desde fuera de él. Los tramos entre nodos de un mismo semáforo
  conjunto no se cuentan: el mismo auto pasaría dos veces
- Un acceso que sale directo de otro semáforo del corredor no lleva
  conteo supuesto: su flujo es el que deja pasar el semáforo anterior.
  Con tasas supuestas iguales en todos los accesos, fijarlo pide más
  autos de los que pueden llegar (en San Claudio, 800 por hora hacia el
  poniente en la central de Derecho cuando de 22 Sur solo salen unos
  500). Si se mide, va en measured y sí se cuenta
- Sentido: adelante es el orden del archivo del corredor (en San
  Claudio, hacia el oriente). Se decide por el ángulo del final del
  tramo contra el eje que va del primer al último semáforo
- Los conteos son totales: a cada acceso se le resta lo que ya pasa por
  él con el tráfico de fondo
- Peatones: randomTrips con pesos por tramo. Con pesos cargados,
  randomTrips ignora su peso por defecto (la longitud), así que aquí se
  escribe la longitud de cada tramo peatonal, multiplicada por
  corridor_weight si está a menos de corridor_buffer_m del corredor
- Misma semilla, misma demanda: randomTrips, duarouter y routeSampler
  reciben la semilla
- Las tasas son constantes durante el escenario; no hay subida ni bajada
  de la hora pico
- La demanda se genera sobre la red del corredor: su zona de estudio si
  la declara (corridor.network.StudyArea), la red completa si no
- La salida de las herramientas queda en Generation.log, junto a las
  rutas


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
import random
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

from corridor.common.Utils import NETWORKS_DIR, load_yaml
from corridor.network.CorridorSpec import (
    corridor_axis,
    load_corridor_spec,
    resolve_signals,
    tls_nodes,
)
from corridor.network.StudyArea import corridor_net_path
from corridor.network.Utils import (
    BACKGROUND_PREFIX,
    BACKGROUND_ROUTES_FILE_NAME,
    CANDIDATE_TRIPS_PER_HOUR,
    CORRIDOR_CANDIDATE_RADIUS_M,
    CORRIDOR_CANDIDATE_TRIPS,
    CORRIDOR_PREFIX,
    CORRIDOR_ROUTES_FILE_NAME,
    COUNTS_FILE_NAME,
    DEMAND_DIR_NAME,
    DETOUR_SLACK_M,
    MAX_DETOUR_RATIO,
    MIN_ENDPOINT_EDGE_M,
    PEDESTRIAN_PREFIX,
    PEDESTRIAN_ROUTES_FILE_NAME,
    SCENARIOS_DIR,
)

SECONDS_PER_HOUR = 3600.0
LOG_FILE_NAME = "Generation.log"

# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Approach:
    """
    Un acceso vehicular a un semáforo del corredor.

    Atributos:
    -------
    edge_id: Tramo de la red por el que llegan los autos
    lanes: Carriles vehiculares del tramo
    main: True si el tramo es de la calle principal del corredor
    forward: True si va en el sentido del archivo del corredor
    internal: True si sale directo de otro semáforo del corredor

    """

    edge_id: str
    lanes: int
    main: bool
    forward: bool
    internal: bool = False


# --------------------------------------------------------------------------
# Accesos y conteos
# --------------------------------------------------------------------------


def corridor_approaches(net, signals, main_street):
    """
    Accesos vehiculares de los semáforos del corredor.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms
    signals: ControlledSignal del corredor, en orden
    main_street: Nombre de la calle principal en la red

    Retorna:
    -------
    list: Approach, en el orden del corredor

    """
    axis = corridor_axis(net, signals)
    axis_x = axis[-1][0] - axis[0][0]
    axis_y = axis[-1][1] - axis[0][1]

    nodes_by_tls = {
        signal.tls_id: {
            node.getID() for node in tls_nodes(net.getTLS(signal.tls_id))
        }
        for signal in signals
    }
    approaches = []
    for signal in signals:
        tls = net.getTLS(signal.tls_id)
        own_nodes = nodes_by_tls[signal.tls_id]
        other_nodes = set().union(
            *(
                nodes
                for tls_id, nodes in nodes_by_tls.items()
                if tls_id != signal.tls_id
            )
        )
        edges = {}
        for in_lane, _, _ in tls.getConnections():
            edge = in_lane.getEdge()
            if edge.getFunction() != "" or not edge.allows("passenger"):
                continue
            if edge.getFromNode().getID() in own_nodes:
                continue
            edges[edge.getID()] = edge
        for edge in edges.values():
            (x0, y0), (x1, y1) = edge.getShape()[-2:]
            approaches.append(
                Approach(
                    edge_id=edge.getID(),
                    lanes=sum(
                        1 for lane in edge.getLanes()
                        if lane.allows("passenger")
                    ),
                    main=edge.getName() == main_street,
                    forward=(x1 - x0) * axis_x + (y1 - y0) * axis_y > 0,
                    internal=edge.getFromNode().getID() in other_nodes,
                )
            )
    return approaches


def approach_counts(approaches, counts_spec, duration_s):
    """
    Autos que deben entrar por cada acceso durante el escenario. Los
    accesos internos solo se cuentan si tienen aforo medido.

    Entradas:
    -------
    approaches: Approach del corredor
    counts_spec: Sección corridor_counts del escenario
    duration_s: Duración del escenario

    Retorna:
    -------
    dict: ID de tramo -> autos en todo el escenario, solo para los
        accesos con conteo

    """
    hours = duration_s / SECONDS_PER_HOUR
    measured = {
        str(edge_id): float(per_hour)
        for edge_id, per_hour in (counts_spec.get("measured") or {}).items()
    }
    main_per_lane = counts_spec["main_per_lane"]
    counts = {}
    for approach in approaches:
        if approach.edge_id in measured:
            per_hour = measured[approach.edge_id]
        elif approach.internal:
            continue
        elif approach.main:
            direction = "forward" if approach.forward else "backward"
            per_hour = main_per_lane[direction] * approach.lanes
        else:
            per_hour = counts_spec["side_per_lane"] * approach.lanes
        counts[approach.edge_id] = per_hour * hours
    return counts


def edge_passes(route_path):
    """
    Cuántas rutas de un archivo pasan por cada tramo.

    Entradas:
    -------
    route_path: Archivo de rutas con vehículos y su ruta completa

    Retorna:
    -------
    Counter: ID de tramo -> rutas que lo usan

    """
    import sumolib

    passes = Counter()
    for vehicle in sumolib.xml.parse(str(route_path), "vehicle"):
        passes.update(vehicle.route[0].edges.split())
    return passes


def write_edge_counts(counts, path, duration_s):
    """
    Escribe los conteos en el formato edgeData que lee routeSampler.

    Entradas:
    -------
    counts: ID de tramo -> autos en todo el escenario
    path: Archivo de salida
    duration_s: Duración del escenario

    Retorna:
    -------
    None

    """
    lines = [
        "<data>",
        f'    <interval id="conteos" begin="0" end="{duration_s}">',
    ]
    for edge_id, count in sorted(counts.items()):
        lines.append(
            f'        <edge id="{edge_id}" entered="{round(count)}"/>'
        )
    lines += ["    </interval>", "</data>", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def write_corridor_trips(net, axis, approaches, path, seed):
    """
    Escribe viajes candidatos dirigidos al corredor: cada uno sale de un
    tramo vehicular cercano, pasa por un acceso elegido al azar y llega
    a otro tramo cercano. duarouter les calcula la ruta.

    Entradas:
    -------
    net: Red de sumolib
    axis: Posiciones de los semáforos del corredor, en orden
    approaches: Approach del corredor
    path: Archivo de viajes de salida
    seed: Semilla del sorteo

    Retorna:
    -------
    None

    """
    approach_ids = {approach.edge_id for approach in approaches}
    endpoints = [
        edge.getID()
        for edge in net.getEdges()
        if edge.getFunction() == ""
        and edge.allows("passenger")
        and edge.getLength() >= MIN_ENDPOINT_EDGE_M
        and edge.getID() not in approach_ids
        and _distance_to_polyline(edge.getShape()[0], axis)
        <= CORRIDOR_CANDIDATE_RADIUS_M
    ]
    rng = random.Random(seed)
    lines = ["<routes>"]
    for index in range(CORRIDOR_CANDIDATE_TRIPS):
        origin, destination = rng.sample(endpoints, 2)
        via = rng.choice(approaches).edge_id
        lines.append(
            f'    <trip id="via{index}" depart="0" from="{origin}" '
            f'via="{via}" to="{destination}"/>'
        )
    lines += ["</routes>", ""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def filter_detours(net, route_paths, out_path):
    """
    Junta rutas candidatas en un archivo, sin las que dan rodeos: las
    que miden más de MAX_DETOUR_RATIO veces la línea recta entre el
    inicio y el final, más DETOUR_SLACK_M.

    Entradas:
    -------
    net: Red de sumolib
    route_paths: Archivos de rutas candidatas
    out_path: Archivo de salida

    Retorna:
    -------
    tuple: (rutas conservadas, rutas descartadas)

    """
    import sumolib

    kept, dropped = 0, 0
    lines = ["<routes>"]
    for route_path in route_paths:
        for vehicle in sumolib.xml.parse(str(route_path), "vehicle"):
            edges = vehicle.route[0].edges.split()
            length_m = sum(net.getEdge(edge).getLength() for edge in edges)
            straight_m = math.dist(
                net.getEdge(edges[0]).getShape()[0],
                net.getEdge(edges[-1]).getShape()[-1],
            )
            if length_m > MAX_DETOUR_RATIO * straight_m + DETOUR_SLACK_M:
                dropped += 1
                continue
            kept += 1
            lines.append(
                f'    <vehicle id="{vehicle.id}" depart="0">'
                f'<route edges="{" ".join(edges)}"/></vehicle>'
            )
    lines += ["</routes>", ""]
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")
    return kept, dropped


# --------------------------------------------------------------------------
# Peatones
# --------------------------------------------------------------------------


def _distance_to_polyline(point, polyline):
    """
    Distancia de un punto a una polilínea.

    Entradas:
    -------
    point: (x_m, y_m)
    polyline: Lista de (x_m, y_m), al menos un punto

    Retorna:
    -------
    float: Distancia en metros

    """
    px, py = point
    if len(polyline) == 1:
        return math.dist(point, polyline[0])
    best = math.inf
    for (ax, ay), (bx, by) in pairwise(polyline):
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        t = 0.0
        if length_sq > 0:
            projection = ((px - ax) * dx + (py - ay) * dy) / length_sq
            t = max(0.0, min(1.0, projection))
        best = min(best, math.dist(point, (ax + t * dx, ay + t * dy)))
    return best


def write_pedestrian_weights(net, axis, pedestrian_spec, prefix, duration_s):
    """
    Escribe los pesos de origen y destino de los peatones para
    randomTrips: la longitud de cada tramo peatonal, multiplicada por
    corridor_weight si alguno de sus puntos está a menos de
    corridor_buffer_m del corredor.

    Entradas:
    -------
    net: Red de sumolib
    axis: Posiciones de los semáforos del corredor, en orden
    pedestrian_spec: Sección pedestrians del escenario
    prefix: Ruta sin sufijo; se escriben <prefix>.src.xml y .dst.xml
    duration_s: Duración del escenario

    Retorna:
    -------
    None

    """
    buffer_m = float(pedestrian_spec["corridor_buffer_m"])
    factor = float(pedestrian_spec["corridor_weight"])
    lines = [
        "<edgedata>",
        f'    <interval begin="0" end="{duration_s}">',
    ]
    for edge in net.getEdges():
        if edge.getFunction() != "" or not edge.allows("pedestrian"):
            continue
        near = any(
            _distance_to_polyline(point, axis) <= buffer_m
            for point in edge.getShape()
        )
        weight = edge.getLength() * (factor if near else 1.0)
        lines.append(
            f'        <edge id="{edge.getID()}" value="{weight:.2f}"/>'
        )
    lines += ["    </interval>", "</edgedata>", ""]
    text = "\n".join(lines)
    for suffix in (".src.xml", ".dst.xml"):
        Path(f"{prefix}{suffix}").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------
# Herramientas de SUMO
# --------------------------------------------------------------------------


def _tool(name):
    """
    Ruta a una herramienta de Python de SUMO.

    Entradas:
    -------
    name: Nombre del archivo, p. ej. 'randomTrips.py'

    Retorna:
    -------
    Path: Ruta dentro de SUMO_HOME/tools

    """
    import sumo

    return Path(sumo.SUMO_HOME) / "tools" / name


def _run_tool(name, args, log_path):
    """
    Corre una herramienta de SUMO con el Python actual y agrega su
    salida al log.

    Entradas:
    -------
    name: Nombre del archivo de la herramienta
    args: Argumentos de línea de comandos
    log_path: Archivo de log

    Retorna:
    -------
    None: Lanza CalledProcessError si la herramienta falla

    """
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n=== {name} {' '.join(map(str, args))}\n")
        log.flush()
        subprocess.run(
            [sys.executable, str(_tool(name)), *map(str, args)],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def route_trips(net_path, trips_path, routes_path, seed, log_path):
    """
    Calcula con duarouter la ruta de cada viaje; descarta los que no
    tienen ruta posible.

    Entradas:
    -------
    net_path: Red de SUMO
    trips_path: Archivo de viajes
    routes_path: Archivo de rutas de salida
    seed: Semilla
    log_path: Archivo de log

    Retorna:
    -------
    None: Lanza CalledProcessError si duarouter falla

    """
    import sumolib

    with open(log_path, "a", encoding="utf-8") as log:
        log.write(f"\n=== duarouter {trips_path}\n")
        log.flush()
        subprocess.run(
            [
                sumolib.checkBinary("duarouter"),
                "-n", str(net_path),
                "--route-files", str(trips_path),
                "-o", str(routes_path),
                "--seed", str(seed),
                "--ignore-errors",
                "--no-step-log",
            ],
            check=True,
            stdout=log,
            stderr=subprocess.STDOUT,
        )


def random_trips(net_path, out_dir, name, seed, duration_s, per_hour,
                 extra_args, log_path):
    """
    Genera viajes al azar con randomTrips y los valida con duarouter.
    Solo se conservan los viajes con ruta posible.

    Entradas:
    -------
    net_path: Red de SUMO
    out_dir: Directorio de salida
    name: Nombre base de los archivos
    seed: Semilla
    duration_s: Duración del escenario
    per_hour: Viajes por hora
    extra_args: Argumentos adicionales de randomTrips
    log_path: Archivo de log

    Retorna:
    -------
    Path: Archivo de rutas validadas

    """
    trips_path = out_dir / f"{name}.trips.xml"
    routes_path = out_dir / f"{name}.rou.xml"
    _run_tool(
        "randomTrips.py",
        [
            "-n", net_path,
            "-o", trips_path,
            "-r", routes_path,
            "--seed", seed,
            "-b", 0,
            "-e", duration_s,
            "--insertion-rate", per_hour,
            "--validate",
            *extra_args,
        ],
        log_path,
    )
    trips_path.unlink(missing_ok=True)
    return routes_path


# --------------------------------------------------------------------------
# Escenario completo
# --------------------------------------------------------------------------


def demand_dir(scenario_name, seed):
    """
    Directorio donde queda la demanda de un escenario y una semilla.

    Entradas:
    -------
    scenario_name: Nombre del escenario, p. ej. 'PeakHour'
    seed: Semilla

    Retorna:
    -------
    Path: networks/<red>/generated/demand/<escenario>/seed_<semilla>

    """
    scenario = load_yaml(SCENARIOS_DIR / f"{scenario_name}.yaml")
    spec = load_corridor_spec(scenario["corridor"])
    return (
        NETWORKS_DIR / spec["network"] / DEMAND_DIR_NAME / scenario_name
        / f"seed_{seed}"
    )


def demand_files(scenario_name, seed):
    """
    Archivos de rutas de un escenario y una semilla, en el orden en que
    SUMO los carga.

    Entradas:
    -------
    scenario_name: Nombre del escenario
    seed: Semilla

    Retorna:
    -------
    list: Rutas de fondo, del corredor y de peatones

    """
    directory = demand_dir(scenario_name, seed)
    return [
        directory / BACKGROUND_ROUTES_FILE_NAME,
        directory / CORRIDOR_ROUTES_FILE_NAME,
        directory / PEDESTRIAN_ROUTES_FILE_NAME,
    ]


def generate_demand(scenario_name, seed):
    """
    Genera los tres archivos de rutas de un escenario con una semilla.

    Entradas:
    -------
    scenario_name: Nombre del escenario, archivo en configs/scenarios/
    seed: Semilla de randomTrips, duarouter y routeSampler

    Retorna:
    -------
    list: Archivos de rutas, como demand_files()

    """
    import sumolib

    scenario = load_yaml(SCENARIOS_DIR / f"{scenario_name}.yaml")
    spec = load_corridor_spec(scenario["corridor"])
    net_path = corridor_net_path(scenario["corridor"])
    if not net_path.is_file():
        raise FileNotFoundError(
            f"No existe {net_path}. Corre scripts/BuildNetwork.sh"
        )
    out_dir = demand_dir(scenario_name, seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / LOG_FILE_NAME
    log_path.unlink(missing_ok=True)
    duration_s = int(scenario["duration_s"])

    net = sumolib.net.readNet(str(net_path), withPrograms=True)
    signals = resolve_signals(net, spec)

    background = scenario["background"]
    background_path = random_trips(
        net_path, out_dir, "Background", seed, duration_s,
        background["vehicles_per_hour"],
        [
            "--fringe-factor", background["fringe_factor"],
            "--random-depart",
            "--prefix", BACKGROUND_PREFIX,
        ],
        log_path,
    )

    counts_spec = scenario["corridor_counts"]
    approaches = corridor_approaches(net, signals, counts_spec["main_street"])
    counts = approach_counts(approaches, counts_spec, duration_s)
    already = edge_passes(background_path)
    counts = {
        edge_id: max(0.0, count - already[edge_id])
        for edge_id, count in counts.items()
    }
    counts_path = out_dir / COUNTS_FILE_NAME
    write_edge_counts(counts, counts_path, duration_s)

    candidates_path = random_trips(
        net_path, out_dir, "Candidates", seed, duration_s,
        CANDIDATE_TRIPS_PER_HOUR * duration_s / SECONDS_PER_HOUR,
        ["--fringe-factor", background["fringe_factor"], "--prefix", "cand"],
        log_path,
    )
    via_trips_path = out_dir / "CorridorCandidates.trips.xml"
    via_routes_path = out_dir / "CorridorCandidates.rou.xml"
    write_corridor_trips(
        net, corridor_axis(net, signals), approaches, via_trips_path, seed
    )
    route_trips(net_path, via_trips_path, via_routes_path, seed, log_path)
    filtered_path = out_dir / "Candidates.filtered.rou.xml"
    kept, dropped = filter_detours(
        net, [candidates_path, via_routes_path], filtered_path
    )
    with open(log_path, "a", encoding="utf-8") as log:
        log.write(
            f"\n=== candidatas: {kept} conservadas, {dropped} con rodeo\n"
        )
    corridor_path = out_dir / CORRIDOR_ROUTES_FILE_NAME
    _run_tool(
        "routeSampler.py",
        [
            "-r", filtered_path,
            "-d", counts_path,
            "-o", corridor_path,
            "--prefix", CORRIDOR_PREFIX,
            "--seed", seed,
            "-b", 0,
            "-e", duration_s,
        ],
        log_path,
    )
    for path in (
        candidates_path, via_trips_path, via_routes_path, filtered_path
    ):
        path.unlink(missing_ok=True)
    Path(f"{via_routes_path}".replace(".rou.xml", ".rou.alt.xml")).unlink(
        missing_ok=True
    )

    pedestrians = scenario["pedestrians"]
    weights_prefix = out_dir / "PedestrianWeights"
    write_pedestrian_weights(
        net, corridor_axis(net, signals), pedestrians, weights_prefix,
        duration_s,
    )
    pedestrian_path = random_trips(
        net_path, out_dir, "Pedestrians", seed, duration_s,
        pedestrians["per_hour"],
        [
            "--pedestrians",
            "--max-distance", pedestrians["max_walk_m"],
            "--weights-prefix", weights_prefix,
            "--random-depart",
            "--prefix", PEDESTRIAN_PREFIX,
        ],
        log_path,
    )
    for suffix in (".src.xml", ".dst.xml"):
        Path(f"{weights_prefix}{suffix}").unlink(missing_ok=True)

    return [background_path, corridor_path, pedestrian_path]


############################# FIN DE DEMAND.PY #################################
################################################################################
