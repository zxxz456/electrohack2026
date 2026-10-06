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
# - Segunda pasada opcional con las correcciones de campo que OSM no
#   trae: ManualEdges.edg.xml (tramos), ManualCrossings.con.xml (cruces)
#   y ManualSignals.csv (semáforos). Se aplica sobre la red de la primera
#   pasada y reconstruye todos los programas de semáforo, para que los
#   cruces nuevos queden dentro del ciclo
# - En ManualSignals.csv, las filas con tl_id vacío se declaran con
#   --tls.set, cada una con su propio programa. Las filas que comparten
#   tl_id forman un solo semáforo conjunto (varios nodos, un programa):
#   se escriben como parche de nodos en generated/ManualSignals.nod.xml,
#   porque tls.join no actúa en la segunda pasada. El nodo creado por un
#   split de ManualEdges.edg.xml no puede ir en un semáforo conjunto:
#   netconvert lee los nodos antes que los tramos
# - Al final verifica que la red tenga todos los semáforos de
#   Signals.csv y ManualSignals.csv; netconvert solo advierte si un nodo
#   no existe
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
# zxxz6       05/10/2026      Semáforos conjuntos desde ManualSignals.csv
# zxxz6       05/10/2026      Segunda pasada con correcciones de campo
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

NET_FILE="generated/Corridor.net.xml.gz"
BASE_FILE="generated/Base.net.xml.gz"

PATCH_ARGS=()
[[ -f ManualEdges.edg.xml ]] && PATCH_ARGS+=(--edge-files ManualEdges.edg.xml)
[[ -f ManualCrossings.con.xml ]] && \
    PATCH_ARGS+=(--connection-files ManualCrossings.con.xml)
if [[ -f ManualSignals.csv ]]; then
    MANUAL_NODES="$(awk -F, 'NR > 1 && $1 != "" && $2 == "" \
        { print $1 }' ManualSignals.csv | paste -sd, -)"
    if [[ -n "$MANUAL_NODES" ]]; then
        PATCH_ARGS+=(--tls.set "$MANUAL_NODES")
        COUNT="$(tr ',' '\n' <<< "$MANUAL_NODES" | wc -l)"
        echo "Semáforos declarados desde ManualSignals.csv: $COUNT"
    fi
    JOINED_NODES="$(awk -F, 'NR > 1 && $1 != "" && $2 != "" \
        { printf "    <node id=\"%s\" type=\"traffic_light\" tl=\"%s\"/>\n", \
          $1, $2 }' ManualSignals.csv)"
    if [[ -n "$JOINED_NODES" ]]; then
        printf '<nodes>\n%s\n</nodes>\n' "$JOINED_NODES" \
            > generated/ManualSignals.nod.xml
        PATCH_ARGS+=(--node-files generated/ManualSignals.nod.xml)
        COUNT="$(wc -l <<< "$JOINED_NODES")"
        echo "Nodos en semáforos conjuntos de ManualSignals.csv: $COUNT"
    fi
fi

echo "Construyendo la red de $CORRIDOR con netconvert..."
if [[ ${#PATCH_ARGS[@]} -eq 0 ]]; then
    netconvert -c Corridor.netccfg "${TLS_ARGS[@]}" -o "$NET_FILE"
else
    netconvert -c Corridor.netccfg "${TLS_ARGS[@]}" -o "$BASE_FILE"
    echo "Aplicando correcciones de campo (segunda pasada)..."
    netconvert -s "$BASE_FILE" "${PATCH_ARGS[@]}" --tls.rebuild \
        -o "$NET_FILE"
fi

echo "Extrayendo polígonos con polyconvert..."
polyconvert -c Corridor.polycfg

if [[ -f Signals.csv ]]; then
    python "$REPO_DIR/scripts/MatchSignals.py" --corridor "$CORRIDOR" --check
fi

echo "Listo. Para verla: sumo-gui -c networks/$CORRIDOR/Corridor.sumocfg"

############################# FIN DE BUILDNETWORK.SH ###########################
################################################################################
