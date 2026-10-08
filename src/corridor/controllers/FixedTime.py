"""
FixedTime.py
========================


Descripción:
------------
Controlador de tiempo fijo, la línea base de todas las comparaciones:
avanza cada etapa cuando cumple su duración fija y no mira el tráfico.
Recorre las mismas etapas que los agentes y pasa por la misma capa de
seguridad, así que la única diferencia con un agente es cuándo decide
avanzar.


Consideraciones:
------------
- Las duraciones vienen de corridor.env.PhasePlan (fixed_duration_s), ya
  recortadas entre el verde mínimo y el máximo
- Decide en la misma rejilla que los agentes: una etapa de 19.8 s dura
  20 s
- Sin desfases entre intersecciones: todas empiezan su ciclo al mismo
  tiempo. PENDIENTE: desfases medidos en campo, si el corredor opera
  coordinado
- Solo elige entre acciones legales; si la que le toca no lo es, toma
  la otra. Con duraciones dentro de los límites eso no ocurre


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

from corridor.env.Utils import ADVANCE, KEEP


class FixedTimeController:
    """
    Avanza cada etapa al cumplir su duración de tiempo fijo.

    Atributos:
    -------
    plans: ID de semáforo -> SignalPlan

    """

    def __init__(self, plans):
        """
        Entradas:
        -------
        plans: ID de semáforo -> SignalPlan

        Retorna:
        -------
        None

        """
        self.plans = plans

    def act(self, statuses, masks, observations=None):
        """
        Elige una acción por semáforo.

        Entradas:
        -------
        statuses: ID de semáforo -> SignalStatus
        masks: ID de semáforo -> (mantener legal, avanzar legal)
        observations: No se usa; existe para compartir la interfaz con
            los agentes

        Retorna:
        -------
        dict: ID de semáforo -> KEEP o ADVANCE

        """
        actions = {}
        for tls_id, plan in self.plans.items():
            status = statuses[tls_id]
            stage = plan.stages[status.stage]
            due = status.time_in_stage_s >= stage.fixed_duration_s
            action = ADVANCE if due else KEEP
            if not masks[tls_id][action]:
                action = KEEP if action == ADVANCE else ADVANCE
            actions[tls_id] = action
        return actions


############################ FIN DE FIXEDTIME.PY ###############################
################################################################################
