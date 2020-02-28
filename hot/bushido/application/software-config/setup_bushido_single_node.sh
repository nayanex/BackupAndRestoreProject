#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="SETUP-BUSHIDO-SINGLE-NODE"
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
    /home/bushido/components/scripts/setup_cluster.sh -clear |& log
    ret=$?
    set +o pipefail
    sleep 1
    return $ret
}

function general_json {
    cat <<JSON
    {
        "bushido.home": "/home/bushido/components/",
        "server.ipaddress": "$INTERNAL_IP",
        "server.hostname": "$HOSTNAME",
        "server.netmask": "$INTERNAL_NETMASK",
        "server.gateway": "$INTERNAL_GATEWAY",
        "server.dns_nameserver": "1.2.3.4",
        "server.dns_search": "openstacklocal",
        "server.ntp_server": "$NTP_EXTERNAL_SERVER",
        "system.update": "1"
    }
JSON
}

# Use Ericsson since we are in a single node cluster for test purposes.
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

function node_json {
    echo -n [\"$INTERNAL_IP:1\"]
}

PYTHON_PATH=$(dirname $(readlink -f $0))/bushido/
URL=https://$INTERNAL_IP:9090/Ronin/rest
USER=admin
PASS=floatingman

log ">>> Step 1 setup General Tab data for $INTERNAL_IP."
post $URL/config/update/general "$(general_json)" || error Failed to update general data
log ">>> General data updated successfully."

log ">>> Step 2 setup site information."
post $URL/cluster/config/update/site "$(site_json)" || error Failed to update site information
log ">>> Site information updated successfully."
EOF

log ">>> Step 3 update cluster configuration - add self."
post $URL/config/writeClusterProperties "$(node_json)" || error Failed to update cluster configuration - add self
log ">>> Cluster configuration updated successfully"

log ">>> Step 4 create single node cluster"
create_cluster || error Failed to create cluster
log ">>> Single node cluster created successfully."

log ">>> Single node cluster configuration and creation completed successfully"
log "============================================================="