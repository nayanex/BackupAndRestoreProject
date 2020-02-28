#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="SETUP-BUSHIDO-CLUSTER"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

# BUSHIDO CLUSTER CONFIGURATION FUNCTIONS

function post {
    local url="$1"
    local data="$2"
    local ret
    set -o pipefail
    python $PYTHON_PATH/bushido_api.py $url $USER $PASS "$data" |& log
    ret=$?
    set +o pipefail
    sleep 1
    return $ret
}

function create_cluster {
    local ret
    set -o pipefail
    /home/bushido/components/scripts/setup_cluster.sh |& log
    ret=$?
    set +o pipefail
    sleep 1
    return $ret
}

# Use Ericsson since we are in a 3 node cluster serving multiple customers.
function site_json {
    cat <<JSON
    {
        "site.company": "Ericsson",
        "site.city": "Atlanta",
        "site.state": "GA",
        "site.country": "US",
        "site.product": "Bushido",
        "site.pass": "weehawken",
        "site.smtpserver": "localhost",
        "site.smtpport": "25",
        "site.smtpauth": "false",
        "site.smtpuser": "myuser",
        "site.smtppassword": "password",
        "isCopyPems": "true"
    }
JSON
}

function cluster_json {
    echo -n [\"$INTERNAL_IP_NODE_TWO:2\", \"$INTERNAL_IP_NODE_THREE:3\"]
}

function node_json {
    echo -n [\"$INTERNAL_IP:1\"]
}

PYTHON_PATH=$(dirname $(readlink -f $0))/bushido/
URL=https://$INTERNAL_IP:9090/Ronin/rest
USER=admin
PASS=floatingman

log ">>> Step 1 update cluster configuration - add nodes."
post $URL/config/writeClusterProperties "$(cluster_json)" || error Failed to update cluster configuration - add nodes
log ">>> Cluster configuration updated successfully."

log ">>> Step 2 push site information to followers."
post $URL/cluster/config/update/site "$(site_json)" || error Failed to update site information
log ">>> Site information updated successfully."
EOF

log ">>> Step 3 update cluster configuration - add self."
post $URL/config/writeClusterProperties "$(node_json)" || error Failed to update cluster configuration - add self
log ">>> Cluster configuration updated successfully"

log ">>> Step 4 create cluster"
create_cluster || error Failed to create cluster
log ">>> Cluster created  successfully."

log ">>> Cluster configuration and creation completed successfully"
log "============================================================="