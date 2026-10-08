"""
TestSafetyLayer.py
========================


Descripción:
------------
Pruebas de la capa de seguridad: ningún paso de simulación viola un
límite de tiempos, con cualquier secuencia de acciones legales. Simulan
miles de segundos con acciones al azar contra una conexión falsa y
revisan segundo a segundo el estado que vería SUMO.


Consideraciones:
------------
- La conexión falsa solo registra los estados; no hay SUMO de por medio
- Se revisa: máscara nunca vacía, verdes dentro de [mínimo, máximo],
  ámbar y todo rojo exactos después de cada avance, cruces en verde
  solo durante el paso peatonal, y que en ningún segundo haya verdes de
  dos etapas distintas a la vez
- También se prueba el controlador de tiempo fijo, que debe recorrer el
  ciclo con sus duraciones fijas


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

import random
from itertools import pairwise

import pytest

from corridor.common.Utils import (
    ALL_RED_S,
    AMBER_S,
    DECISION_INTERVAL_S,
    PED_START_S,
)
from corridor.controllers.FixedTime import FixedTimeController
from corridor.env.SafetyLayer import SafetyLayer
from corridor.env.Utils import ADVANCE, GREEN_CHARS, KEEP

SIMULATED_S = 6000
STEP_S = 1.0


class FakeConnection:
    """
    Conexión falsa: registra el último estado de cada semáforo.

    Atributos:
    -------
    trafficlight: La misma conexión, para imitar conn.trafficlight
    states: ID de semáforo -> último estado recibido

    """

    def __init__(self):
        self.trafficlight = self
        self.states = {}

    def setRedYellowGreenState(self, tls_id, state):
        self.states[tls_id] = state


def _greens(state):
    return {link for link, char in enumerate(state) if char in GREEN_CHARS}


def _run(plans, choose, seconds=SIMULATED_S):
    """
    Corre la capa de seguridad segundo a segundo con un controlador.

    Entradas:
    -------
    plans: ID de semáforo -> SignalPlan
    choose: Función (statuses, masks) -> acciones
    seconds: Segundos a simular

    Retorna:
    -------
    tuple: (estados por semáforo y segundo, avances como pares
        (segundo, tiempo en la etapa, etapa), máscaras vistas)

    """
    connection = FakeConnection()
    layer = SafetyLayer(connection, plans)
    layer.reset()
    timeline = {tls_id: [] for tls_id in plans}
    advances = {tls_id: [] for tls_id in plans}
    masks_seen = []
    for second in range(seconds):
        if second % DECISION_INTERVAL_S == 0:
            statuses = {tls_id: layer.status(tls_id) for tls_id in plans}
            masks = {tls_id: layer.action_mask(tls_id) for tls_id in plans}
            masks_seen.extend(masks.values())
            actions = choose(statuses, masks)
            for tls_id, action in actions.items():
                if action == ADVANCE:
                    status = statuses[tls_id]
                    advances[tls_id].append(
                        (second, status.time_in_stage_s, status.stage)
                    )
            layer.apply(actions)
        for tls_id in plans:
            assert connection.states[tls_id] == layer.status(tls_id).state
            timeline[tls_id].append(connection.states[tls_id])
        layer.tick(STEP_S)
    return timeline, advances, masks_seen


def _random_legal(seed):
    rng = random.Random(seed)

    def choose(statuses, masks):
        return {
            tls_id: rng.choice([a for a in (KEEP, ADVANCE) if mask[a]])
            for tls_id, mask in masks.items()
        }

    return choose


@pytest.fixture
def plans(plan_18_sur, plan_mid_block):
    return {plan.tls_id: plan for plan in (plan_18_sur, plan_mid_block)}


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_random_legal_actions_never_break_limits(plans, seed):
    timeline, advances, masks_seen = _run(plans, _random_legal(seed))

    assert all(any(mask) for mask in masks_seen)
    for tls_id, plan in plans.items():
        states = timeline[tls_id]
        stage_greens = [_greens(stage.green_state) for stage in plan.stages]

        # Nunca hay verdes de dos etapas distintas a la vez.
        for state in states:
            assert any(_greens(state) <= greens for greens in stage_greens)

        for second, time_in_stage_s, stage_index in advances[tls_id]:
            stage = plan.stages[stage_index]
            assert time_in_stage_s >= stage.min_green_s
            assert time_in_stage_s <= stage.max_green_s

            # Ámbar y todo rojo exactos, luego el verde de la siguiente.
            (amber, _), (all_red, _) = plan.transition(stage_index)
            following = plan.stages[plan.next_stage(stage_index)]
            window = states[second : second + AMBER_S + ALL_RED_S + 1]
            if len(window) < AMBER_S + ALL_RED_S + 1:
                continue
            amber_window = window[:AMBER_S]
            all_red_window = window[AMBER_S : AMBER_S + ALL_RED_S]
            assert amber_window == [amber] * AMBER_S
            assert all_red_window == [all_red] * ALL_RED_S
            assert window[-1] == following.green_state


def test_vehicle_links_never_skip_amber(plans):
    timeline, _, _ = _run(plans, _random_legal(3))
    for tls_id, plan in plans.items():
        crossings = {
            link
            for stage in plan.stages
            for link, char in enumerate(stage.green_state)
            if stage.clearance_state[link] != char
        }
        states = timeline[tls_id]
        for before, after in pairwise(states):
            for link, (old, new) in enumerate(zip(before, after)):
                if link in crossings:
                    continue
                if old in GREEN_CHARS and new not in GREEN_CHARS:
                    assert new == "y"


def test_crossings_are_green_only_during_walk(plans):
    timeline, _, _ = _run(plans, _random_legal(4))
    for tls_id, plan in plans.items():
        crossing_links = {
            link
            for stage in plan.stages
            for link, char in enumerate(stage.green_state)
            if stage.clearance_state[link] != char
        }
        for link in crossing_links:
            run = 0
            for state in timeline[tls_id]:
                run = run + 1 if state[link] in GREEN_CHARS else 0
                assert run <= PED_START_S


def test_illegal_action_is_rejected(plan_18_sur):
    layer = SafetyLayer(FakeConnection(), {plan_18_sur.tls_id: plan_18_sur})
    layer.reset()
    assert layer.action_mask(plan_18_sur.tls_id) == (True, False)
    with pytest.raises(ValueError):
        layer.apply({plan_18_sur.tls_id: ADVANCE})


def test_keep_forever_is_cut_at_max_green(plan_18_sur):
    plans = {plan_18_sur.tls_id: plan_18_sur}

    def keep_when_legal(statuses, masks):
        return {
            tls_id: KEEP if mask[KEEP] else ADVANCE
            for tls_id, mask in masks.items()
        }

    _, advances, _ = _run(plans, keep_when_legal, seconds=600)
    for _, time_in_stage_s, stage_index in advances[plan_18_sur.tls_id]:
        assert time_in_stage_s == plan_18_sur.stages[stage_index].max_green_s


def test_fixed_time_follows_its_durations(plans):
    controller = FixedTimeController(plans)

    def choose(statuses, masks):
        return controller.act(statuses, masks)

    _, advances, _ = _run(plans, choose, seconds=1200)
    for tls_id, plan in plans.items():
        assert advances[tls_id]
        for _, time_in_stage_s, stage_index in advances[tls_id]:
            fixed_s = plan.stages[stage_index].fixed_duration_s
            assert fixed_s <= time_in_stage_s < fixed_s + DECISION_INTERVAL_S


########################### FIN DE TESTSAFETYLAYER.PY ##########################
################################################################################
