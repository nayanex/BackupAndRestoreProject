#!/bin/bash

function usage {
    local ret=${1:0}
    echo "Usage: $0 SED [COMPANY]"
    echo "Configure the Bushido cluster using the Ronin API, where:"
    echo "SED is the path to the ENM SED."
    echo "COMPANY is the Company name.  If not supplied the Deployment ID from the SED will be used."
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

function site_json {
    cat <<JSON
    {
        "site.company": "$COMPANY",
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

function general_json {
    cat <<JSON
    {
        "bushido.home": "/home/bushido/components/",
        "server.ipaddress": "$IP",
        "server.hostname": "$HOSTNAME",
        "server.netmask": "$NM",
        "server.gateway": "$GW",
        "server.dns_nameserver": "1.2.3.4",
        "server.dns_search": "openstacklocal",
        "server.ntp_server": "$NTP",
        "system.update": "1"  
    }
JSON
}

function node_json {
    echo -n [\"$IP:1\"]
}


ETH0=/etc/sysconfig/network-scripts/ifcfg-eth0
SED=$1

[[ $1 =~ .*-h.* ]] && usage
[[ $(whoami) != bushido ]]   && error This script must be ran as bushido user
[[ $# -eq 1 ||  $# -eq 2 ]]  || usage 1
[[ -f $SED ]] || error "SED not found"
[[ -f $ETH0 ]] || error "$ETH0 not found"


IP=$(grep IPADDR $ETH0  | sed 's/"//g' | cut -d= -f 2)
GW=$(grep GATEWAY $ETH0 | sed 's/"//g' | cut -d= -f 2)
NM=$(grep NETMASK $ETH0 | sed 's/"//g' | cut -d= -f 2)
NTP=$(grep ntp_external_servers $SED|cut -d\" -f 4| cut -d, -f -1)
HOSTNAME=$(hostname)

[[ -z $IP ]]  && error IPADDR not found in $ETH0
[[ -z $GW ]]  && error GATEWAY not found in $ETH0
[[ -z $NM ]]  && error NETMASK not found in $ETH0
[[ -z $NTP ]] && error NTP entry not found in SED

if [[ -n "$2" ]] ; then
    COMPANY=$2
else
    COMPANY=$(grep deployment_id $SED|cut -d\" -f 4| cut -d, -f -1)
    [[ -z $COMPANY ]] && error deployment_id not found in SED
fi

LOG=${0}.log
PYTHONPATH=$(pwd)/Python2API
URL=https://${IP}:9090/Ronin/rest
USER=admin
PASS=floatingman

log ">>> Started $0 with arguments $@"
log ">>> Step 1 update general data"
post $URL/config/update/general "$(general_json)" || error Failed to update general data
log ">>> General data updated succesfully"

log ">>> Step 2 update site information"
post $URL/cluster/config/update/site "$(site_json)" || error Failed to update site information
log ">>> Site information updated succesfully"
EOF

log ">>> Step 3 update cluster configuration"
post $URL/config/writeClusterProperties  "$(node_json)" || error Failed to update cluster configuration
log ">>> Cluster confguration updated succesfully"

log ">>> Step 4 create cluster"
create_cluster || error Failed to create cluster
log ">>> Cluster created  succesfully"

log ">>> Cluster configuration and creation completed successfully"
log "============================================================="
