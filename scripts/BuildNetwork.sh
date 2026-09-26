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

echo "Construyendo la red de $CORRIDOR con netconvert..."
netconvert -c Corridor.netccfg

echo "Extrayendo polígonos con polyconvert..."
polyconvert -c Corridor.polycfg

echo "Listo. Para verla: sumo-gui -c networks/$CORRIDOR/Corridor.sumocfg"

############################# FIN DE BUILDNETWORK.SH ###########################
################################################################################
