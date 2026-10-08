"""
SafetyLayer.py
========================


Descripción:
------------
Capa de seguridad de los semáforos controlados. Es el único código del
proyecto que cambia el estado de un semáforo en SUMO. Recibe de cada
controlador una acción por semáforo (mantener o avanzar), calcula qué
acciones son legales antes de que el controlador elija, y aplica las
etapas con su paso peatonal, despeje, ámbar y todo rojo.


Consideraciones:
------------
- Máscara: avanzar es legal cuando la etapa lleva al menos su verde
  mínimo; mantener es legal mientras otro intervalo de decisión no
  rebase el verde máximo. Si ninguna de las dos lo fuera (una etapa con
  verde mínimo fuera de la rejilla de decisión), mantener queda legal:
  nunca hay una máscara vacía
- Una acción ilegal lanza ValueError. La máscara se aplica antes de
  elegir; corregir la acción aquí escondería un error del controlador
- El ámbar más el todo rojo dura un intervalo de decisión, así que al
  decidir el semáforo nunca está en transición. Si estuviera, solo
  mantener es legal
- El tiempo avanza con tick(), una vez por paso de simulación. SUMO
  solo recibe un estado cuando cambia
- Las duraciones efectivas caen en la rejilla de decisión: una etapa con
  verde mínimo de 19.8 s puede avanzar a los 20 s
- La conexión es cualquier objeto con trafficlight.setRedYellowGreenState:
  una conexión de TraCI, libsumo, o una conexión falsa en las pruebas


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

from dataclasses import dataclass, field

from corridor.common.Utils import DECISION_INTERVAL_S
from corridor.env.Utils import ADVANCE, KEEP

# --------------------------------------------------------------------------
# Tipos
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SignalStatus:
    """
    Lo que un controlador puede saber del estado de un semáforo.

    Atributos:
    -------
    stage: Índice de la etapa actual en el plan
    time_in_stage_s: Segundos de verde de la etapa actual
    in_transition: True durante el ámbar o el todo rojo
    state: Estado que muestra el semáforo en SUMO

    """

    stage: int
    time_in_stage_s: float
    in_transition: bool
    state: str


@dataclass
class _SignalRuntime:
    """
    Estado interno de un semáforo dentro de la capa de seguridad.

    Atributos:
    -------
    stage: Índice de la etapa actual
    time_in_stage_s: Segundos de verde de la etapa actual
    transition: Pares [estado, segundos restantes] pendientes del
        cambio de etapa; vacía fuera de una transición
    shown: Último estado enviado a SUMO

    """

    stage: int = 0
    time_in_stage_s: float = 0.0
    transition: list = field(default_factory=list)
    shown: str = ""


# --------------------------------------------------------------------------
# Capa de seguridad
# --------------------------------------------------------------------------


class SafetyLayer:
    """
    Aplica las etapas de los semáforos controlados y hace cumplir sus
    límites de tiempos.

    Atributos:
    -------
    plans: ID de semáforo -> SignalPlan

    """

    def __init__(self, connection, plans):
        """
        Prepara la capa sin tocar SUMO; reset() pone los semáforos en su
        primera etapa.

        Entradas:
        -------
        connection: Conexión con trafficlight.setRedYellowGreenState
        plans: ID de semáforo -> SignalPlan

        Retorna:
        -------
        None

        """
        self._connection = connection
        self.plans = plans
        self._runtime = {}

    def reset(self):
        """
        Pone cada semáforo al inicio del verde de su primera etapa.

        Entradas:
        -------
        None

        Retorna:
        -------
        None

        """
        self._runtime = {tls_id: _SignalRuntime() for tls_id in self.plans}
        for tls_id in self.plans:
            self._show(tls_id, self._stage_state(tls_id))

    def action_mask(self, tls_id):
        """
        Acciones legales de un semáforo en este momento.

        Entradas:
        -------
        tls_id: ID del semáforo

        Retorna:
        -------
        tuple: (mantener es legal, avanzar es legal), indexable por
            KEEP y ADVANCE

        """
        runtime = self._runtime[tls_id]
        if runtime.transition:
            return (True, False)
        stage = self.plans[tls_id].stages[runtime.stage]
        advance = runtime.time_in_stage_s >= stage.min_green_s
        keep = (
            runtime.time_in_stage_s + DECISION_INTERVAL_S <= stage.max_green_s
            or not advance
        )
        return (keep, advance)

    def apply(self, actions):
        """
        Aplica una acción por semáforo. Avanzar inicia el ámbar en este
        mismo instante; mantener no cambia nada.

        Entradas:
        -------
        actions: ID de semáforo -> KEEP o ADVANCE. Los semáforos que no
            aparecen mantienen su etapa

        Retorna:
        -------
        None: Lanza ValueError si alguna acción es ilegal

        """
        for tls_id, action in actions.items():
            if action not in (KEEP, ADVANCE):
                raise ValueError(f"{tls_id}: acción desconocida {action}")
            if not self.action_mask(tls_id)[action]:
                runtime = self._runtime[tls_id]
                raise ValueError(
                    f"{tls_id}: acción {action} ilegal en la etapa "
                    f"{runtime.stage} a los {runtime.time_in_stage_s} s"
                )
        for tls_id, action in actions.items():
            if action == ADVANCE:
                runtime = self._runtime[tls_id]
                plan = self.plans[tls_id]
                runtime.transition = [
                    [state, duration_s]
                    for state, duration_s in plan.transition(runtime.stage)
                ]
                self._show(tls_id, runtime.transition[0][0])

    def tick(self, step_s):
        """
        Avanza el reloj de todos los semáforos un paso de simulación y
        envía a SUMO los estados que cambian: fin del paso peatonal,
        ámbar a todo rojo y todo rojo a la siguiente etapa.

        Entradas:
        -------
        step_s: Duración del paso de simulación que acaba de correr

        Retorna:
        -------
        None

        """
        for tls_id, runtime in self._runtime.items():
            if runtime.transition:
                runtime.transition[0][1] -= step_s
                if runtime.transition[0][1] > 1e-9:
                    continue
                runtime.transition.pop(0)
                if runtime.transition:
                    self._show(tls_id, runtime.transition[0][0])
                    continue
                runtime.stage = self.plans[tls_id].next_stage(runtime.stage)
                runtime.time_in_stage_s = 0.0
            else:
                runtime.time_in_stage_s += step_s
            self._show(tls_id, self._stage_state(tls_id))

    def status(self, tls_id):
        """
        Estado de un semáforo para los controladores y la observación.

        Entradas:
        -------
        tls_id: ID del semáforo

        Retorna:
        -------
        SignalStatus: Etapa, tiempo en ella, transición y estado visible

        """
        runtime = self._runtime[tls_id]
        return SignalStatus(
            stage=runtime.stage,
            time_in_stage_s=runtime.time_in_stage_s,
            in_transition=bool(runtime.transition),
            state=runtime.shown,
        )

    def _stage_state(self, tls_id):
        """
        Estado de la etapa actual según su tiempo: paso o despeje.

        Entradas:
        -------
        tls_id: ID del semáforo

        Retorna:
        -------
        str: Estado de SUMO

        """
        runtime = self._runtime[tls_id]
        stage = self.plans[tls_id].stages[runtime.stage]
        return stage.state_at(runtime.time_in_stage_s)

    def _show(self, tls_id, state):
        """
        Envía un estado a SUMO si es distinto del que ya muestra.

        Entradas:
        -------
        tls_id: ID del semáforo
        state: Estado de SUMO

        Retorna:
        -------
        None

        """
        runtime = self._runtime[tls_id]
        if state != runtime.shown:
            self._connection.trafficlight.setRedYellowGreenState(
                tls_id, state
            )
            runtime.shown = state


########################### FIN DE SAFETYLAYER.PY ##############################
################################################################################
