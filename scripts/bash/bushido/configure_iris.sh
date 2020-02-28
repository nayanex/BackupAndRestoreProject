#!/bin/bash

function usage {
    local ret=${1:0}
    echo "Usage: $0 SED ENM_JSON"
    echo "Configure the Bushido cluster using the Ronin API, where:"
    echo "SED is the path to the ENM SED."
    echo "ENM_JSON is the path to the enm.json file TODO: FROM WHERE"
    echo "The script must be ran as bushido user"
    exit $ret
}

function error {
    log ERROR: $@
    exit 1
}

function now {
    date "+%Y-%m-%d %H:%M:%S "
}   

function log {
    local log=/dev/null
    [[ -n "$LOG" ]] && log=$LOG
    [[ $# -gt 0 ]] && echo $(now) $@ | tee -a $log
    [[ -p /dev/stdin ]] && tee >( while read line ; do echo $(now) $line >> $log ; done  )
}

function post {
    local url="$1"
    local data="$2"
    local ret
    set -o pipefail
    python $PYTHONPATH/api.py $url $USER $PASS POST "$data" |& log
    ret=$?
    set +o pipefail
    return $ret
}

function get {
    local url="$1"
    local ret
    set -o pipefail
    python $PYTHONPATH/api.py $url $USER $PASS GET |& log
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

function role_json {
    local role=$1
    cat <<JSON
        [{"role":"$role","description":"$role","level":"100"}]
JSON
}

#            "teams":"{\\"APPLICATION_ADMIN\\":\\"$TEAM_ID\\"}",

function app_json {
    local app=$1
    cat <<JSON
    {
        "application":{
            "orgId":"$ORG_ID",
            "createTime":"$(date +%Y-%m-%dT%H:%M:%S.000Z)",
            "description":"$app",
            "state":"PROD",
            "teams":"{\\"APPLICATION_ADMIN\\":\\"$TEAM_ID\\"}",
            "agents":"{}",
            "isAdminRole":false,
            "region":"$DEP_ID",
            "name":"$app",
            "appType":"STATIC"
        }
    }
JSON
}

function apps_to_view_json {
    cat <<JSON
    {
        "name": "Default View",
        "viewId": "597c4d11-13db-31e4-bb62-cd8a7112cf88",
        "isDefault": true,
        "appViews": [{"id": "$ORG_ID",
                      "isAllApps": true }]
    }
JSON
}

function view_json {
    cat <<JSON
    {
        "name": "Default View",
        "viewId": "597c4d11-13db-31e4-bb62-cd8a7112cf88",
        "isDefault": true,
        "appViews": [{"id": "$ORG_ID", "isAllApps": true }]
    }
JSON
}
 
function create_enm_synonym_file {
    cat > $SYNONYM_FILE <<SYNONYMS
{
"serviceregistry":["servicereg"],
"cmevents":["cmevnts"],
"lvs":["lvsrouter"],
"nfsnorollback":["nfsnrbk"],
"nfspmlinks":["nfspmlink"],
"scripting":["scp"]
}
SYNONYMS
    [[ $? -eq 0 ]] || error "Failed to create $SYNONYM_FILE"
    log Running ./create_role_list.py -i $ENM -o $AGENT_ROLE_FILE -s $SYNONYM_FILE -p ${DEP_ID}-
    ./create_role_list.py -i $ENM -o $AGENT_ROLE_FILE -s $SYNONYM_FILE -p ${DEP_ID}-
}

LOG=${0}.log
ETH0=/etc/sysconfig/network-scripts/ifcfg-eth0
SED=$1
ENM=$2

[[ $1 =~ .*-h.* ]] && usage  
[[ $(whoami) != bushido ]]   && error This script must be ran as bushido user
[[ $# -eq 2 ]]  || usage
[[ -f $SED ]]   || error "SED not found"
[[ -f $ETH0 ]]  || error "$ETH0 not found"
[[ -f $ENM ]]   || error "$ENM  not found"

USER=admin
PASS=floatingman
PYTHONPATH=$(pwd)/Python2API   # EDDERS

IP=$(grep IPADDR $ETH0  | sed 's/"//g' | cut -d= -f 2)
KOTOBA=https://${IP}:8090/kotoba/rest
DEP_ID=$(grep deployment_id $SED|cut -d\" -f 4| cut -d, -f -1)

AGENT_ROLE_FILE=agent_roles.txt
SYNONYM_FILE=synonym.json

log ">>> Started $0 with arguments $@"
log ">>> Step 1 Create synonym file $SYNONYM_FILE"
create_enm_synonym_file || error "Failed to create $AGENT_ROLE_FILE"
log ">>> Synonym file created succesfully"

log ">>> Step  2 Create Organisation Definition for Tenancy"
post $KOTOBA/orgdef/update "$(org_def_json)" || error Failed to create organisation definition
log ">>> Organisation Definition created successfully"

log ">>> Step 3 Create Instance of Tenancy"
post $KOTOBA/org/add "$(org_json)" || error Failed to create tenancy instance
log ">>> Instance of Tenancy created successfully"

log ">>> Step 4 Create Region" # Atlanta/Staging04 consider for 1-n bushido
post $KOTOBA/applications/saveregion "$(region_json)" || Failed to create region
log ">>> Region created successfully"

log ">>> Step 5 Get Organisation"
RESP=$(get $KOTOBA/org/all) || error Failed to get organisation ID
# TODO ORG_ID=$(grep '"nodeId"' <<< "$RESP" | cut -d\" -f 4)
ORG_ID=$(grep $DEP_ID -A 5 <<< "$RESP" | grep nodeId | cut -d\" -f 4)
log ">>> Organisation retrieved successfully"

log ">>> Step 6 Get Default Team"
RESP=$(get $KOTOBA/team/all) || error Failed to get Team ID
TEAM_ID=$(grep '"teamid"' <<< "$RESP" | cut -d\" -f 4)
log ">>> Default Team retrieved successfully"

log ">>> Step 7 Create Agent Roles"
while read role ; do
    post $KOTOBA/serverrole/addServerRole "$(role_json $role)" || error Failed to add role $role
done < <(awk -F ":" ' { print $2 } ' $AGENT_ROLE_FILE | sort -u )
log ">>> Agent Roles created successfully"

log ">>> Step 8 Create Applications"
while read app ; do
    post $KOTOBA/applications/update/admin "$(app_json $app)" || error Failed to create application $app
done < <(awk -F ":" ' { print $3 } ' $AGENT_ROLE_FILE | sort -u )
log ">>> Applications created successfully"

log ">>> Step 9 Update View"
post $KOTOBA/user/updateView "$(view_json)" || error Failed to update view
log ">>> View updated successfully"

log ">>> Iris configuration completed successfully"
log "============================================================="

