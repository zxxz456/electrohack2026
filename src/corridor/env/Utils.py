"""
Utils.py
========================


Descripción:
------------
Constantes del módulo env: caracteres de estado de los semáforos de
SUMO, acciones de los agentes y el archivo de etapas declaradas a mano.


Consideraciones:
------------
- Los estados de SUMO tienen un carácter por enlace. Aquí solo se usan
  G (verde con prioridad), g (verde que cede el paso), y (ámbar) y
  r (rojo); las etapas declaradas a mano solo admiten G, g y r


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       05/10/2026      Creación


"""

# --------------------------------------------------------------------------
# Estados de semáforo de SUMO
# --------------------------------------------------------------------------

GREEN_CHARS = frozenset("Gg")
AMBER_CHAR = "y"
RED_CHAR = "r"
STAGE_CHARS = frozenset("Ggr")

# --------------------------------------------------------------------------
# Acciones de los agentes
# --------------------------------------------------------------------------

# Cada intervalo de decisión: mantener la etapa o avanzar a la siguiente
# del ciclo. El orden de las etapas es fijo, como en un controlador real.
KEEP = 0
ADVANCE = 1
ACTIONS = (KEEP, ADVANCE)

# --------------------------------------------------------------------------
# Archivos
# --------------------------------------------------------------------------

# Etapas declaradas a mano, dentro de networks/<corredor>/.
STAGES_FILE_NAME = "Stages.yaml"


############################## FIN DE UTILS.PY #################################
################################################################################
