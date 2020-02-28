#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="CONFIGURE-IRIS"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

function post {
    local url="$1"
    local data="$2"
    local ret
    set -o pipefail
    python $PYTHON_PATH/cluster/bushido_api.py $url $USER $PASS "$data" |& log
    ret=$?
    set +o pipefail
    return $ret
}

function org_def_json {
    cat <<JSON
    {
        "name":"TENANCY",
        "description":"Tenancy",
        "canHaveApps":true
    }
JSON
}

function org_json {
    cat <<JSON
    {
        "name":"$DEP_ID",
        "type":"TENANCY",
        "code":"$DEP_ID",
        "description":"$DEP_ID",
        "parent":Null
    }
JSON
}

function region_json {
    cat <<JSON
    {
        "name":"$DEP_ID",
        "description":"$DEP_ID Region"
    }
JSON
}

USER=admin
PASS=floatingman
PYTHON_PATH=$(dirname $(readlink -f $0))/bushido/

KOTOBA=https://$INTERNAL_IP:8090/kotoba/rest
DEP_ID=Atlanta

# TODO: add missing steps (i.e. Agent creation) when it is agreed how they are going to be created.
# refer to "ecm-tools/scripts/bash/bushido/configure_iris.sh" for some other functions.
log ">>> Step 1 Create Organisation Definition for Tenancy"
post $KOTOBA/orgdef/update "$(org_def_json)" || error Failed to create organisation definition
log ">>> Organisation Definition created successfully"

log ">>> Step 2 Create Instance of Tenancy"
post $KOTOBA/org/add "$(org_json)" || error Failed to create tenancy instance
log ">>> Instance of Tenancy created successfully"

log ">>> Step 3 Create Region" # Atlanta/Staging04 consider for 1-n bushido
post $KOTOBA/applications/saveregion "$(region_json)" || Failed to create region
log ">>> Region created successfully"

log ">>> Iris configuration completed successfully"
log "============================================================="

