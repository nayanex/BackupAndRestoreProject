#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="CONFIGURE-BUSHIDO-SOFTWARE"
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

PYTHON_PATH=$(dirname $(readlink -f $0))/bushido/
URL=https://$INTERNAL_IP:9090/Ronin/rest
USER=admin
PASS=floatingman

log ">>> Set General Tab data for $INTERNAL_IP."
post $URL/config/update/general "$(general_json)" || error Failed to update general data
log ">>> General data updated successfully."