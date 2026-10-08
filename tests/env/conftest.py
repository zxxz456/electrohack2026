"""
conftest.py
========================


Descripción:
------------
Datos compartidos por las pruebas del módulo env: programas de
netconvert sintéticos y los planes de etapas que salen de ellos.


Consideraciones:
------------
- Los programas copian la forma de los que genera netconvert 1.27.1
  para 18 Sur (dos etapas con cruces peatonales) y para el cruce
  peatonal a media cuadra (autos y peatones en etapas separadas)


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

from corridor.env.PhasePlan import build_signal_plan, stages_from_program

# 18 Sur: paso, despeje peatonal y ámbar por etapa. Los enlaces 11 a 14
# son cruces peatonales.
PROGRAM_18_SUR = [
    ("rrrgGGgGGggGGrr", 35.0),
    ("rrrgGGgGGggrrrr", 5.0),
    ("rrryyyyyyyyrrrr", 5.0),
    ("gggrrrrrrrrrGGG", 35.0),
    ("gggrrrrrrrrrrrr", 5.0),
    ("yyyrrrrrrrrrrrr", 5.0),
]
CROSSINGS_18_SUR_M = {11: 6.4, 12: 6.4, 13: 6.4, 14: 6.4}

# Cruce peatonal a media cuadra: el enlace 4 es el cruce.
PROGRAM_MID_BLOCK = [
    ("GGGGr", 77.0),
    ("yyyyr", 3.0),
    ("rrrrG", 5.0),
    ("rrrrr", 5.0),
]
CROSSINGS_MID_BLOCK_M = {4: 12.8}


@pytest.fixture
def program_18_sur():
    return list(PROGRAM_18_SUR)


@pytest.fixture
def crossings_18_sur_m():
    return dict(CROSSINGS_18_SUR_M)


@pytest.fixture
def program_mid_block():
    return list(PROGRAM_MID_BLOCK)


@pytest.fixture
def crossings_mid_block_m():
    return dict(CROSSINGS_MID_BLOCK_M)


@pytest.fixture
def plan_18_sur():
    return build_signal_plan(
        "18_sur",
        stages_from_program(PROGRAM_18_SUR),
        CROSSINGS_18_SUR_M,
        link_count=15,
    )


@pytest.fixture
def plan_mid_block():
    return build_signal_plan(
        "media_cuadra",
        stages_from_program(PROGRAM_MID_BLOCK),
        CROSSINGS_MID_BLOCK_M,
        link_count=5,
    )


############################# FIN DE CONFTEST.PY ###############################
################################################################################
