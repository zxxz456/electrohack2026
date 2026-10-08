"""
PhasePlan.py
========================


Descripción:
------------
Etapas de cada semáforo controlado y los estados con que se pasa de una
a otra. Es la única fuente de fases del proyecto: el controlador de
tiempo fijo y los agentes recorren las mismas etapas en el mismo orden
cíclico, y la capa de seguridad las aplica con el mismo ámbar, todo
rojo, verde mínimo y verde máximo. Así una diferencia en los resultados
viene de cuándo se cambia de etapa, no de qué etapas existen.


Consideraciones:
------------
- Por defecto las etapas salen del programa que generó netconvert: cada
  racha de fases sin ámbar y con algún verde es una etapa. netconvert
  parte cada etapa en paso y despeje peatonal; aquí el despeje se
  calcula, así que de la racha se toma el primer estado y la suma de
  duraciones
- Si netconvert arma mal un semáforo, sus etapas se declaran en
  networks/<corredor>/Stages.yaml y reemplazan a las del programa. Pasa
  en semáforos conjuntos de varios nodos: en Facultad de Derecho
  netconvert le da verde a cada calzada por separado
- Paso y despeje peatonal: los cruces de una etapa están en verde los
  primeros PED_START_S segundos y después en rojo, mientras los autos
  siguen en verde, para que quien empezó a cruzar termine. El verde
  mínimo de la etapa cubre los dos: PED_START_S más el cruce más largo
  entre PED_SPEED_MPS
- Transición: ámbar de AMBER_S en los enlaces que pierden el verde y
  luego todo rojo de ALL_RED_S. Los enlaces con verde en las dos etapas
  no se interrumpen
- La duración de tiempo fijo se recorta al intervalo entre el verde
  mínimo y el máximo, porque la capa de seguridad aplica esos límites a
  todos los controladores
- Las funciones de etapas reciben datos simples (estados, duraciones,
  longitudes) y no la red de SUMO, para poder probarlas sin construirla


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

from dataclasses import dataclass

from corridor.common.Utils import (
    ALL_RED_S,
    AMBER_S,
    MAX_GREEN_S,
    MIN_GREEN_S,
    PED_SPEED_MPS,
    PED_START_S,
    load_yaml,
)
from corridor.env.Utils import (
    AMBER_CHAR,
    GREEN_CHARS,
    RED_CHAR,
    STAGE_CHARS,
)

# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Stage:
    """
    Una etapa de un semáforo: movimientos compatibles que reciben verde
    juntos.

    Atributos:
    -------
    green_state: Estado de SUMO durante el paso peatonal, con los
        cruces de la etapa en verde
    clearance_state: Estado después del paso: los mismos verdes
        vehiculares y los cruces en rojo
    walk_s: Duración del paso peatonal; 0 si la etapa no tiene cruces
    min_green_s: Verde mínimo de la etapa
    max_green_s: Verde máximo de la etapa
    fixed_duration_s: Duración en el controlador de tiempo fijo

    """

    green_state: str
    clearance_state: str
    walk_s: float
    min_green_s: float
    max_green_s: float
    fixed_duration_s: float

    def state_at(self, time_in_stage_s):
        """
        Estado que muestra el semáforo a cierto tiempo de iniciada la
        etapa: paso peatonal al principio, despeje después.

        Entradas:
        -------
        time_in_stage_s: Segundos desde que empezó el verde de la etapa

        Retorna:
        -------
        str: Estado de SUMO, un carácter por enlace

        """
        if time_in_stage_s < self.walk_s:
            return self.green_state
        return self.clearance_state


@dataclass(frozen=True)
class SignalPlan:
    """
    Las etapas de un semáforo en su orden cíclico.

    Atributos:
    -------
    tls_id: ID del semáforo en la red
    stages: Etapas en orden, como tupla de Stage

    """

    tls_id: str
    stages: tuple

    def next_stage(self, index):
        """
        Índice de la etapa que sigue en el ciclo.

        Entradas:
        -------
        index: Índice de la etapa actual

        Retorna:
        -------
        int: Índice de la siguiente etapa

        """
        return (index + 1) % len(self.stages)

    def transition(self, index):
        """
        Estados entre el fin de una etapa y el verde de la siguiente.
        Parte del despeje de la etapa actual: para cuando se permite
        avanzar, el paso peatonal ya terminó.

        Entradas:
        -------
        index: Índice de la etapa que termina

        Retorna:
        -------
        list: Pares (estado, duración_s): ámbar y todo rojo

        """
        current = self.stages[index].clearance_state
        following = self.stages[self.next_stage(index)].green_state
        amber, all_red = transition_states(current, following)
        return [(amber, float(AMBER_S)), (all_red, float(ALL_RED_S))]


# --------------------------------------------------------------------------
# Etapas
# --------------------------------------------------------------------------


def _is_stage_phase(state):
    """
    Indica si una fase de un programa de netconvert es parte de una
    etapa: sin ámbar y con algún verde.

    Entradas:
    -------
    state: Estado de SUMO de la fase

    Retorna:
    -------
    bool: True si la fase pertenece a una etapa

    """
    return AMBER_CHAR not in state and any(
        char in GREEN_CHARS for char in state
    )


def stages_from_program(phases):
    """
    Agrupa las fases de un programa de netconvert en etapas. Cada racha
    de fases de etapa da una etapa con su primer estado y la suma de
    duraciones. El programa es cíclico: si empieza a media racha, esa
    racha se une con la del final.

    Entradas:
    -------
    phases: Pares (estado, duración_s) en el orden del programa

    Retorna:
    -------
    list: Pares (estado, duración_s), uno por etapa

    """
    flags = [_is_stage_phase(state) for state, _ in phases]
    if all(flags):
        return [(phases[0][0], sum(duration for _, duration in phases))]

    # Rota para empezar justo después de la última fase de transición;
    # así ninguna racha queda partida entre el final y el inicio.
    last_transition = max(i for i, flag in enumerate(flags) if not flag)
    start = (last_transition + 1) % len(phases)
    rotated = phases[start:] + phases[:start]

    stages = []
    run_state, run_duration_s = None, 0.0
    for state, duration_s in rotated:
        if _is_stage_phase(state):
            if run_state is None:
                run_state = state
            run_duration_s += duration_s
        elif run_state is not None:
            stages.append((run_state, run_duration_s))
            run_state, run_duration_s = None, 0.0
    if run_state is not None:
        stages.append((run_state, run_duration_s))
    return stages


def clearance_state(state, crossing_links):
    """
    Estado de despeje peatonal: el mismo estado con los cruces en rojo.

    Entradas:
    -------
    state: Estado de SUMO de la etapa
    crossing_links: Índices de enlace que son cruces peatonales

    Retorna:
    -------
    str: Estado con los cruces en rojo

    """
    return "".join(
        RED_CHAR if link in crossing_links else char
        for link, char in enumerate(state)
    )


def transition_states(current, following):
    """
    Estados de ámbar y todo rojo entre dos etapas. Los enlaces con verde
    en las dos conservan su verde; los que lo pierden pasan a ámbar y
    luego a rojo; el resto queda en rojo.

    Entradas:
    -------
    current: Estado que muestra el semáforo al terminar la etapa
    following: Estado de verde de la siguiente etapa

    Retorna:
    -------
    tuple: (estado de ámbar, estado de todo rojo)

    """
    amber, all_red = [], []
    for now, upcoming in zip(current, following, strict=True):
        if now in GREEN_CHARS and upcoming in GREEN_CHARS:
            amber.append(now)
            all_red.append(now)
        elif now in GREEN_CHARS:
            amber.append(AMBER_CHAR)
            all_red.append(RED_CHAR)
        else:
            amber.append(RED_CHAR)
            all_red.append(RED_CHAR)
    return "".join(amber), "".join(all_red)


def stage_timing(state, crossing_lengths_m):
    """
    Paso peatonal, verde mínimo y verde máximo de una etapa. Sin cruces
    en verde, el verde mínimo es MIN_GREEN_S. Con cruces, cubre el paso
    y el despeje del cruce más largo. El verde máximo nunca queda por
    debajo del mínimo.

    Entradas:
    -------
    state: Estado de verde de la etapa
    crossing_lengths_m: Índice de enlace de cada cruce -> longitud, m

    Retorna:
    -------
    tuple: (walk_s, min_green_s, max_green_s)

    """
    lengths_m = [
        length_m
        for link, length_m in crossing_lengths_m.items()
        if state[link] in GREEN_CHARS
    ]
    if not lengths_m:
        return 0.0, float(MIN_GREEN_S), float(MAX_GREEN_S)
    min_green_s = max(
        float(MIN_GREEN_S), PED_START_S + max(lengths_m) / PED_SPEED_MPS
    )
    return float(PED_START_S), min_green_s, max(float(MAX_GREEN_S), min_green_s)


def validate_stages(tls_id, stage_specs, link_count):
    """
    Verifica que unas etapas sirvan para la capa de seguridad: al menos
    dos, un carácter válido por enlace, y todo enlace con verde en
    alguna etapa. Un enlace que nunca recibe verde deja a sus autos o
    peatones esperando para siempre.

    Entradas:
    -------
    tls_id: ID del semáforo, para el mensaje de error
    stage_specs: Pares (estado, duración_s), uno por etapa
    link_count: Número de enlaces que controla el semáforo

    Retorna:
    -------
    None: Lanza ValueError con la causa si algo falla

    """
    if len(stage_specs) < 2:
        raise ValueError(
            f"{tls_id}: se necesitan al menos dos etapas, hay "
            f"{len(stage_specs)}"
        )
    for state, _ in stage_specs:
        if len(state) != link_count:
            raise ValueError(
                f"{tls_id}: el estado {state} tiene {len(state)} "
                f"enlaces y el semáforo controla {link_count}"
            )
        invalid = set(state) - STAGE_CHARS
        if invalid:
            raise ValueError(
                f"{tls_id}: caracteres no válidos en una etapa: "
                + "".join(sorted(invalid))
            )
    unserved = [
        link
        for link in range(link_count)
        if not any(state[link] in GREEN_CHARS for state, _ in stage_specs)
    ]
    if unserved:
        raise ValueError(
            f"{tls_id}: enlaces sin verde en ninguna etapa: "
            + ", ".join(str(link) for link in unserved)
        )


def build_signal_plan(tls_id, stage_specs, crossing_lengths_m, link_count):
    """
    Arma el plan de un semáforo a partir de sus etapas.

    Entradas:
    -------
    tls_id: ID del semáforo en la red
    stage_specs: Pares (estado, duración_s), uno por etapa, en orden
    crossing_lengths_m: Índice de enlace de cada cruce -> longitud, m
    link_count: Número de enlaces que controla el semáforo

    Retorna:
    -------
    SignalPlan: Etapas con sus estados y tiempos

    """
    validate_stages(tls_id, stage_specs, link_count)
    crossing_links = frozenset(crossing_lengths_m)
    stages = []
    for state, duration_s in stage_specs:
        walk_s, min_green_s, max_green_s = stage_timing(
            state, crossing_lengths_m
        )
        stages.append(
            Stage(
                green_state=state,
                clearance_state=clearance_state(state, crossing_links),
                walk_s=walk_s,
                min_green_s=min_green_s,
                max_green_s=max_green_s,
                fixed_duration_s=min(
                    max(float(duration_s), min_green_s), max_green_s
                ),
            )
        )
    return SignalPlan(tls_id=tls_id, stages=tuple(stages))


# --------------------------------------------------------------------------
# Lectura desde la red
# --------------------------------------------------------------------------


def load_signal_plans(net, tls_ids, stages_path=None):
    """
    Arma los planes de varios semáforos de una red de SUMO. Usa las
    etapas de Stages.yaml cuando el semáforo aparece ahí, y las del
    programa de netconvert en otro caso.

    Entradas:
    -------
    net: Red de sumolib leída con withPrograms, withInternal y
        withPedestrianConnections
    tls_ids: IDs de los semáforos que controlan los agentes
    stages_path: Ruta a Stages.yaml; None o inexistente si no hay
        etapas declaradas a mano

    Retorna:
    -------
    dict: ID de semáforo -> SignalPlan

    """
    overrides = {}
    if stages_path is not None and stages_path.is_file():
        overrides = load_yaml(stages_path) or {}

    plans = {}
    for tls_id in tls_ids:
        tls = net.getTLS(tls_id)
        crossing_lengths_m = {}
        link_count = 0
        for _, out_lane, link in tls.getConnections():
            link_count = max(link_count, link + 1)
            if out_lane.getEdge().getFunction() == "crossing":
                crossing_lengths_m[link] = out_lane.getLength()

        if tls_id in overrides:
            stage_specs = [
                (stage["state"], float(stage["duration_s"]))
                for stage in overrides[tls_id]
            ]
        else:
            program = next(iter(tls.getPrograms().values()))
            stage_specs = stages_from_program(
                [
                    (phase.state, float(phase.duration))
                    for phase in program.getPhases()
                ]
            )
        plans[tls_id] = build_signal_plan(
            tls_id, stage_specs, crossing_lengths_m, link_count
        )
    return plans


############################ FIN DE PHASEPLAN.PY ###############################
################################################################################
