"""
TestPhasePlan.py
========================


Descripción:
------------
Pruebas de las etapas de los semáforos: agrupamiento de programas de
netconvert, paso y despeje peatonal, estados de transición, tiempos
mínimos y máximos, y validación de etapas declaradas a mano. Usan
estados sintéticos, sin red de SUMO; la última prueba carga el corredor
real si la red está construida.


Consideraciones:
------------
- Los programas sintéticos y sus planes vienen de conftest.py
- La prueba con la red real se salta si no se ha corrido
  scripts/BuildNetwork.sh


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

import pytest

from corridor.common.Utils import (
    ALL_RED_S,
    AMBER_S,
    DECISION_INTERVAL_S,
    MAX_GREEN_S,
    MIN_GREEN_S,
    NETWORKS_DIR,
    PED_SPEED_MPS,
    PED_START_S,
)
from corridor.env.PhasePlan import (
    build_signal_plan,
    clearance_state,
    stage_timing,
    stages_from_program,
    transition_states,
)


def test_amber_and_all_red_fill_one_decision_interval():
    assert AMBER_S + ALL_RED_S == DECISION_INTERVAL_S


def test_program_groups_walk_and_clearance_into_one_stage(program_18_sur):
    stages = stages_from_program(program_18_sur)
    assert stages == [
        ("rrrgGGgGGggGGrr", 40.0),
        ("gggrrrrrrrrrGGG", 40.0),
    ]


def test_all_red_phase_is_not_a_stage(program_mid_block):
    stages = stages_from_program(program_mid_block)
    assert stages == [("GGGGr", 77.0), ("rrrrG", 5.0)]


def test_run_split_across_program_end_is_merged():
    program = [
        ("rG", 5.0),
        ("ry", 3.0),
        ("Gr", 30.0),
        ("yr", 3.0),
        ("rG", 10.0),
    ]
    stages = stages_from_program(program)
    assert sorted(stages) == [("Gr", 30.0), ("rG", 15.0)]


def test_clearance_turns_only_crossings_red(crossings_18_sur_m):
    state = clearance_state("rrrgGGgGGggGGrr", set(crossings_18_sur_m))
    assert state == "rrrgGGgGGggrrrr"


def test_transition_keeps_links_green_in_both_stages():
    amber, all_red = transition_states("GGgr", "GrrG")
    assert amber == "Gyyr"
    assert all_red == "Grrr"


def test_stage_without_crossings_uses_vehicle_limits():
    walk_s, min_green_s, max_green_s = stage_timing("GGGGr", {4: 12.8})
    assert walk_s == 0.0
    assert min_green_s == MIN_GREEN_S
    assert max_green_s == MAX_GREEN_S


def test_crossing_sets_walk_and_min_green_by_length(crossings_mid_block_m):
    walk_s, min_green_s, _ = stage_timing("rrrrG", crossings_mid_block_m)
    assert walk_s == PED_START_S
    assert min_green_s == pytest.approx(PED_START_S + 12.8 / PED_SPEED_MPS)


def test_very_long_crossing_raises_max_green():
    _, min_green_s, max_green_s = stage_timing("rG", {1: 80.0})
    assert min_green_s > MAX_GREEN_S
    assert max_green_s == min_green_s


def test_fixed_duration_is_clipped_between_min_and_max(plan_mid_block):
    vehicles, pedestrians = plan_mid_block.stages
    assert vehicles.fixed_duration_s == MAX_GREEN_S
    assert pedestrians.fixed_duration_s == pedestrians.min_green_s


def test_crossing_is_green_only_during_walk(plan_mid_block):
    pedestrians = plan_mid_block.stages[1]
    assert pedestrians.state_at(0.0) == "rrrrG"
    assert pedestrians.state_at(PED_START_S) == "rrrrr"


def test_transition_starts_from_clearance(plan_18_sur):
    plan = plan_18_sur
    (amber, amber_s), (all_red, all_red_s) = plan.transition(0)
    assert amber == "rrryyyyyyyyrrrr"
    assert all_red == "r" * 15
    assert (amber_s, all_red_s) == (AMBER_S, ALL_RED_S)
    assert plan.next_stage(1) == 0


@pytest.mark.parametrize(
    "stage_specs",
    [
        [("GGr", 30.0)],
        [("GGr", 30.0), ("rrGr", 30.0)],
        [("GGr", 30.0), ("rrY", 30.0)],
        [("Grr", 30.0), ("rGr", 30.0)],
    ],
    ids=["una etapa", "longitud", "caracter", "enlace sin verde"],
)
def test_invalid_stages_are_rejected(stage_specs):
    with pytest.raises(ValueError):
        build_signal_plan("malo", stage_specs, {}, link_count=3)


NET_PATH = NETWORKS_DIR / "puebla" / "generated" / "Corridor.net.xml.gz"


@pytest.mark.skipif(not NET_PATH.is_file(), reason="red sin construir")
def test_san_claudio_corridor_loads():
    import sumolib

    from corridor.env.PhasePlan import load_signal_plans
    from corridor.env.Utils import STAGES_FILE_NAME
    from corridor.network.CorridorSpec import (
        load_corridor_spec,
        resolve_signals,
    )

    spec = load_corridor_spec("SanClaudio")
    net = sumolib.net.readNet(
        str(NET_PATH),
        withPrograms=True,
        withInternal=True,
        withPedestrianConnections=True,
    )
    signals = resolve_signals(net, spec)
    plans = load_signal_plans(
        net,
        [signal.tls_id for signal in signals],
        NETWORKS_DIR / spec["network"] / STAGES_FILE_NAME,
    )
    assert len(signals) == len(spec["signals"])
    derecho = plans["san_claudio_derecho"]
    assert [stage.green_state for stage in derecho.stages] == [
        "GGGGGGGrrr",
        "rrrrrrrGGG",
    ]
    for plan in plans.values():
        for stage in plan.stages:
            assert stage.min_green_s <= stage.fixed_duration_s
            assert stage.fixed_duration_s <= stage.max_green_s


############################ FIN DE TESTPHASEPLAN.PY ###########################
################################################################################
