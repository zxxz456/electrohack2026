#!/usr/bin/env bash
#
# BuildNetwork.sh
# ========================
#
#
# Descripción:
# ------------
# Construye la red vial de SUMO y sus polígonos a partir del extracto de
# OSM versionado en networks/<corredor>/. La salida va a generated/, que
# no se versiona: cada integrante la reconstruye con este script.
#
#
# Consideraciones:
# ------------
# - Uso: scripts/BuildNetwork.sh [corredor], por defecto puebla
# - Requiere el entorno virtual activo, porque las configuraciones usan
#   SUMO_HOME para encontrar los mapas de tipos de OSM
# - Orden fijo: primero netconvert, luego polyconvert, que necesita la
#   red para proyectar los polígonos
# - Los semáforos que OSM no trae se leen de Signals.csv (filas con
#   status added) y se pasan a netconvert con --tls.set. Ese archivo lo
#   genera scripts/MatchSignals.py a partir del inventario municipal
# - Las filas already_in_osm no se pasan: esos cruces ya son semáforo, y
#   declararlos otra vez parte los semáforos conjuntos de OSM (varios
#   nodos, un programa) en semáforos independientes y desincronizados
# - Al final verifica que la red tenga todos los semáforos de
#   Signals.csv; netconvert solo advierte si un nodo no existe
#
#
# Metadatos:
# ----------
# * Autor: zxxz6 (Bryan Violante Arriaga)
# * Versión: 1.0.0
#
#
# Historial:
# ------------
# Autor       Fecha           Descripción
# zxxz6       26/09/2026      Semáforos del inventario y verificación final
# zxxz6       26/09/2026      Creación
#

set -euo pipefail

CORRIDOR="${1:-puebla}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NETWORK_DIR="$REPO_DIR/networks/$CORRIDOR"

: "${SUMO_HOME:?SUMO_HOME no esta definido. Activa .venv primero}"

if [[ ! -d "$NETWORK_DIR" ]]; then
    echo "No existe el corredor: $NETWORK_DIR" >&2
    exit 1
fi

cd "$NETWORK_DIR"
mkdir -p generated

TLS_ARGS=()
if [[ -f Signals.csv ]]; then
    TLS_NODES="$(awk -F, 'NR > 1 && $2 == "added" && $1 != "" \
        { print $1 }' Signals.csv | paste -sd, -)"
    if [[ -n "$TLS_NODES" ]]; then
        TLS_ARGS=(--tls.set "$TLS_NODES")
        COUNT="$(tr ',' '\n' <<< "$TLS_NODES" | wc -l)"
        echo "Semáforos declarados desde Signals.csv: $COUNT"
    fi
fi

echo "Construyendo la red de $CORRIDOR con netconvert..."
netconvert -c Corridor.netccfg "${TLS_ARGS[@]}"

echo "Extrayendo polígonos con polyconvert..."
polyconvert -c Corridor.polycfg

if [[ -f Signals.csv ]]; then
    python "$REPO_DIR/scripts/MatchSignals.py" --corridor "$CORRIDOR" --check
fi

echo "Listo. Para verla: sumo-gui -c networks/$CORRIDOR/Corridor.sumocfg"

############################# FIN DE BUILDNETWORK.SH ###########################
################################################################################
