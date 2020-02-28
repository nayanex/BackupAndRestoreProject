#!/bin/bash


# +++ GLOBALS +++
NL=$'\n'
OPT1=StrictHostKeyChecking=no
OPT2=UserKnownHostsFile=/dev/null
USER=cloud-user
VMS=""
WHITELIST=false
BLACKLIST=false
export ID=0

# +++ GLOBALS FROM ARGS +++
#LOG=${3:-${0}.log}
LOG=${0}.log
KEY=${1}
VM_FILE=${2}

# +++ FUNCTIONS +++
function int {
    [[ $1 =~ ^[0-9]+$ ]]
}

# DISPLAY USAGE
function usage {
    local ret=${1:0}
    echo "Usage: $0 PRIVATE_KEY [--whitelist=FILE | --blacklist=FILE]"
    echo "Check if Bushido agent is running on consul members."
    echo "The FILE argument for --whitelist or --blacklist can be consul members output or just a list of"
    echo "hostnames (newline separated)."
    echo "If --blacklist is supplied then the blacklisted hosts will be excluded from the install."
    echo "If --whitelist is supplied then only those hosts will be included for the install." 
    exit $ret
}

# LOG TO STDOUT AND OPTIONALLY TO LOGFILE IF '$LOG' IS DEFINED
# LOG WORKS WITH ARGS AND/OR PIPED STDIN
function log {
    local tstamp=$(date "+%Y-%m-%d %H:%M:%S")                     # SET LOG TIMESTAMP
    #local prefix="$tstamp [$BASHPID]"                             # ADD PID IN CASE OF BG PROCS
    local pid
    printf -v pid "%06d" $BASHPID                                # ADD PID IN CASE OF BG PROCS
    printf -v pid "%07d" $ID  # TODO TEST
    local prefix="$tstamp [$pid]"

    local log=/dev/null                                           # NO LOGFILE
    [[ -n "$LOG" ]] && log=$LOG                                   # USE LOGFILE IF '$LOG' SET
    [[ $# -gt 0 ]] && echo $prefix $@ | tee -a $log               # LOG ARGS
    [[ -p /dev/stdin ]] && { sed "s/^/$prefix /g"| tee -a $log;}  # LOG PIPED STDIN

}

# LOG ERROR AND EXIT
function error {
    log ERROR: $@
    exit 1
}


function parse_node_file {
    awk ' { print $1 } ' $NODE__FILE 

}

# GET HOSTNAMES OF ENM VMS FROM CONSUL
function get_enm_nodes {
    log "Entered >>> get_enm_nodes()"
    VMS=$(consul members|grep -v vnflaf-services | grep ' alive ' | cut -d: -f 1 )
    [[ -z "$VMS" ]] && error "No VM IPs retrieved from consul"

    # HANDLE BLACK/WHITE LIST
    local node_list=$([[ -n "$VM_FILE" ]] && grep "[A-Za-z]" "$VM_FILE")
    node_list=$(awk '{ print $1 }' <<<"$node_list" | tr '\n' '|' | sed 's/|$//g')
    if [[ $WHITELIST == true ]] ; then
        [[ -z $node_list ]] && error Whitelist has no valid entries
        log "Only including the following nodes: $node_list"
        VMS=$(grep -wE "$node_list" <<< "$VMS") 
    elif [[ $BLACKLIST == true ]] ; then
        [[ -z $node_list ]] && error Whitelist has no valid entries
        log "Excluding the following nodes: $node_list"
        VMS=$(grep -vwE "$node_list" <<< "$VMS") 
    fi
    [[ -z "$VMS" ]] && error "No VMs to selected"
}

function is_agent_running {
    local host=$1
    local ip="$2"
    local ret
    local bush=com.cixsoft.bushido.utils.Samurai
    set -o pipefail
    ssh -o $OPT1 -o $OPT2 -i $KEY ${USER}@${ip} "ps -ef | grep -v grep | grep -q $bush" 2>/dev/null || log Bushido Agent NOT Running on $host
    ret=$?
    set +o pipefail
    return $ret
}
 
function for_each_vm_run_in_bg {
    log "Entered >>> for_each_vm_run_in_bg($2 $3)"
    local vm_list="$1"
    local fn=$2
    local fn_args="$3"
    local i host ip

    # cannot use while read as it messes ssh tty
    # local -a vms=($VMS)  EDDERS TODO NEW
    local -a vms=($vm_list)

    for (( i=0; i<${#vms[@]} ; i+=2 )) ; do
        host="${vms[i]}"
        ip="${vms[i+1]}"
        ID=$(ip2id $ip)

        $fn $host $ip "$fn_args" &          # TODO: CAN WE LOG THIS
        while [ $(jobs | wc -l) -ge 20 ] ; do sleep 1 ; done
    done
    wait
    ID=0
    log Finished calling $fm for each VM
}


function ip2id
{
    local a b c d
    { IFS=. read a b c d; } <<< $1
    echo $(((((  b << 8) | c) << 8) | d)); 
}


# +++ PARSE ARGS +++
[[ $1 =~ .*-h.* ]] && usage
[[ -f "$KEY" ]]    || usage 1
[[ -n "$3" ]]      && usage 1
[[ "$VM_FILE" =~ --whitelist* ]] && WHITELIST=true
[[ "$VM_FILE" =~ --blacklist* ]] && BLACKLIST=true

# Strip --*list= from argument
VM_FILE=$(cut -d= -f2- <<< $VM_FILE)
[[ -n "$VM_FILE" ]] && ([[ -f "$VM_FILE" ]] || usage 1)

# +++ MAIN +++
log Started $0 with arguments: $@ at $(date)
get_enm_nodes
for_each_vm_run_in_bg "$VMS" is_agent_running
log $0 Completed OK
log '====================================================================================='

