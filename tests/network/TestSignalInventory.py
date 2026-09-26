"""
TestSignalInventory.py
========================


Descripción:
------------
Pruebas del agrupamiento de postes del inventario en intersecciones y
de su emparejamiento con cruces de la red. Usan datos sintéticos en
metros, sin red de SUMO, para que corran en cualquier máquina.


Consideraciones:
------------
- Las distancias de los casos están elegidas alrededor de los radios de
  corridor.network.Utils; si cambian los radios, estos casos marcan qué
  comportamiento se movió


Metadatos:
----------
* Autor: zxxz6 (Bryan Violante Arriaga)
* Versión: 1.0.0


Historial:
------------
Autor       Fecha           Descripción
zxxz6       26/09/2026      Pruebas de select_matches
zxxz6       26/09/2026      Creación


"""

from corridor.network.SignalInventory import (
    Junction,
    Pole,
    SignalMatch,
    cluster_poles,
    match_group,
    read_signal_node_ids,
    select_matches,
    write_signals,
)
from corridor.network.Utils import (
    MATCH_RADIUS_M,
    MIN_APPROACH_STREETS,
    POLE_LINK_RADIUS_M,
    SAME_STREETS_LINK_RADIUS_M,
    STATUS_ADDED,
    STATUS_ALREADY_IN_OSM,
    STATUS_UNMATCHED,
    normalize_street,
)

SAN_CLAUDIO_14_SUR = frozenset({"SAN CLAUDIO", "14 SUR"})
SAN_CLAUDIO_18_SUR = frozenset({"SAN CLAUDIO", "18 SUR"})


def _pole(x_m, streets=SAN_CLAUDIO_14_SUR, pedestrian_heads=0):
    """
    Crea un poste sobre el eje x.

    Entradas:
    -------
    x_m: Posición en x, metros
    streets: Calles del cruce
    pedestrian_heads: Cabezas peatonales

    Retorna:
    -------
    Pole: Poste de prueba

    """
    return Pole(x_m, 0.0, streets, pedestrian_heads)


def _identity(x_m, y_m):
    """
    Proyección de prueba: devuelve las coordenadas sin cambio.

    Entradas:
    -------
    x_m, y_m: Coordenadas

    Retorna:
    -------
    tuple: (x_m, y_m)

    """
    return x_m, y_m


# --------------------------------------------------------------------------
# normalize_street
# --------------------------------------------------------------------------


def test_normalize_street_strips_accents_and_spaces():
    """
    Verifica que variantes de un mismo nombre queden iguales.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    assert normalize_street(" Río  Papagayo ") == "RIO PAPAGAYO"
    assert normalize_street(None) == ""


# --------------------------------------------------------------------------
# cluster_poles
# --------------------------------------------------------------------------


def test_close_poles_form_one_intersection():
    """
    Verifica que postes dentro de POLE_LINK_RADIUS_M queden juntos,
    incluso encadenados.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    step = POLE_LINK_RADIUS_M - 1
    poles = [_pole(0.0), _pole(step), _pole(2 * step)]
    assert len(cluster_poles(poles)) == 1


def test_same_streets_join_within_larger_radius():
    """
    Verifica que postes con las mismas calles se unan hasta
    SAME_STREETS_LINK_RADIUS_M.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    gap = SAME_STREETS_LINK_RADIUS_M - 1
    assert len(cluster_poles([_pole(0.0), _pole(gap)])) == 1


def test_different_streets_60_m_apart_stay_apart():
    """
    Reproduce el caso de San Claudio: intersecciones vecinas a unos
    60 m, con calles distintas, no deben fusionarse.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    poles = [_pole(0.0), _pole(60.0, SAN_CLAUDIO_18_SUR)]
    assert len(cluster_poles(poles)) == 2


# --------------------------------------------------------------------------
# match_group
# --------------------------------------------------------------------------


def test_prefers_signalized_junction_in_radius():
    """
    Verifica que un cruce ya semaforizado gane aunque haya otro más
    cercano sin semáforo.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    junctions = [
        Junction("near", 2.0, 0.0, has_signal=False),
        Junction("signalized", 10.0, 0.0, has_signal=True),
    ]
    match = match_group([_pole(0.0)], junctions, _identity)
    assert match.node_id == "signalized"
    assert match.status == STATUS_ALREADY_IN_OSM


def test_without_signal_takes_nearest_junction():
    """
    Verifica que sin semáforos en el radio se elija el más cercano.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    junctions = [
        Junction("far", 20.0, 0.0, has_signal=False),
        Junction("near", 5.0, 0.0, has_signal=False),
    ]
    match = match_group(
        [_pole(0.0, pedestrian_heads=2), _pole(4.0, pedestrian_heads=1)],
        junctions,
        _identity,
    )
    assert match.node_id == "near"
    assert match.status == STATUS_ADDED
    assert match.poles == 2
    assert match.pedestrian_heads == 3


def test_outside_radius_does_not_match():
    """
    Verifica que un cruce más lejos que MATCH_RADIUS_M no se use.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    junctions = [Junction("far", MATCH_RADIUS_M + 5, 0.0, True)]
    match = match_group([_pole(0.0)], junctions, _identity)
    assert match.status == STATUS_UNMATCHED
    assert match.node_id == ""


# --------------------------------------------------------------------------
# select_matches
# --------------------------------------------------------------------------

# Área de prueba en coordenadas de _identity: x entre 0 y 100.
AREA = (0.0, -10.0, 100.0, 10.0)


def _select(x_m, approach_streets):
    """
    Corre select_matches con un grupo y un cruce en la misma posición.

    Entradas:
    -------
    x_m: Posición del grupo y del cruce sobre el eje x
    approach_streets: Calles que llegan al cruce

    Retorna:
    -------
    list: SignalMatch seleccionados

    """
    junctions = [Junction("j", x_m, 0.0, False, approach_streets)]
    return select_matches([[_pole(x_m)]], junctions, _identity, AREA)


def test_inside_area_keeps_partial_junction():
    """
    Verifica que dentro del área entre cualquier cruce emparejado; ahí
    un semáforo con una sola calle es legítimo (cruce peatonal).

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    selected = _select(50.0, approach_streets=1)
    assert [match.inside_area for match in selected] == [True]


def test_outside_area_drops_partial_junction():
    """
    Verifica que en la orilla se descarte un cruce al que le falta la
    calle transversal.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    assert _select(150.0, MIN_APPROACH_STREETS - 1) == []


def test_outside_area_keeps_real_crossing():
    """
    Verifica que en la orilla entre un cruce con las dos calles, marcado
    como fuera del área.

    Entradas:
    -------
    None

    Retorna:
    -------
    None

    """
    selected = _select(150.0, MIN_APPROACH_STREETS)
    assert [match.inside_area for match in selected] == [False]


# --------------------------------------------------------------------------
# Signals.csv
# --------------------------------------------------------------------------


def test_csv_round_trip_skips_unmatched(tmp_path):
    """
    Verifica que read_signal_node_ids lea lo que escribe write_signals y
    omita las filas sin nodo.

    Entradas:
    -------
    tmp_path: Directorio temporal de pytest

    Retorna:
    -------
    None

    """
    rows = [
        SignalMatch("a", STATUS_ADDED, "X, con coma", 19.0, -98.2, 3, 0, 1.0),
        SignalMatch("", STATUS_UNMATCHED, "Y", 19.1, -98.1, 1, 0, 90.0),
    ]
    path = tmp_path / "Signals.csv"
    write_signals(rows, path)
    assert read_signal_node_ids(path) == ["a"]


####################### FIN DE TESTSIGNALINVENTORY.PY ##########################
################################################################################
