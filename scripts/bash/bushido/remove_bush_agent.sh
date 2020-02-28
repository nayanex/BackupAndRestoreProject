#!/bin/bash


# NOTES: bushido-agent-1769-GA.x86_64.rpm
# +++ GLOBALS +++
NL=$'\n'
OPT=StrictHostKeyChecking=no
USER=cloud-user
VMS=""
WHITELIST=false
BLACKLIST=false

export ID=0

# LOCAL PATHS
LOCAL_TMP_DIR=/tmp
LOCAL_REMOVE_SCRIPT=${LOCAL_TMP_DIR}/remove_agent.sh

# REMOTE PATHS
REMOTE_TMP_DIR=/var/tmp
REMOTE_REMOVE_SCRIPT=${REMOTE_TMP_DIR}/remove_agent.sh

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
    echo "       $0 PRIVATE_KEY  [--whitelist=FILE | --blacklist=FILE]"
    echo "Remove bushido agent from consul members."
    echo "The FILE argument for --whitelist or --blacklist can be consul members output or just a list of"
    echo "hostnames (newline separated)."
    echo "If --blacklist is supplied then the blacklisted hosts will be excluded from the removal."
    echo "If --whitelist is supplied then only those hosts will be included for the removal." 
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

# COPY FILES ONTO HOST AS USER TO /TMP 
function remote_copy {
    log "Entered >>> remote_copy($@)"
    local host=$1
    shift
    local files="$@"
    log Copying $files as $USER to $host
    log scp -o $OPT -i $KEY $files $USER@$host:$REMOTE_TMP_DIR
    scp -o $OPT -i $KEY $files $USER@$host:$REMOTE_TMP_DIR
    if [[ $? -eq 0 ]] ; then
        log $files copied to $host successfully
    else
        log WARNING Failed to copy $files to $host
    fi
}

function ssh_user {
    log "Entered >>> ssh_user($@)"
    local host=$1
    local cmd="$2"
    local ret
    log Running $cmd as $USER on $host
    set -o pipefail
    log ssh -ttt -o $OPT -i $KEY ${USER}@${host} $cmd 
    ssh -ttt -o $OPT -i $KEY ${USER}@${host} $cmd | log
    ret=$?
    set +o pipefail

    if [[ $ret -eq 0 ]] ; then
        log Ran $cmd on $host successfully
    else
        log WARNING Failed to run $cmd on $host
    fi
    return $ret
}

function ssh_user_no_log {
    local host=$1
    local cmd="$2"
    local ret
    set -o pipefail
    ssh -ttt -o $OPT -i $KEY ${USER}@${host} $cmd 
    ret=$?
    set +o pipefail
    return $ret
}

# RUN COMMAND ON HOST AS ROOT USER
function ssh_root {
    log "Entered >>> ssh_root($@)"
    local host=$1
    local cmd="$2"
    log  Running $cmd as root on $host
    python -c 'import pty, sys; pty.spawn(sys.argv[1:])' ssh -o $OPT -i $KEY ${USER}@${host} \
    < <( sleep 1
         echo sudo -i
         sleep 0.5
         echo ${cmd}
         echo exit
         echo exit
    ) |  tr -cd '\11\12\40-\176' | sed 's/]0;//g' | log
    # TODO WORK OUT HOW TO CHECK FOR FAILURE HERE
    # MAYBE TEE INTO VARIABLE AS WELL AS LOG AND CHECK FOR FAIL STRINGS
}


function create_remove_script {
    log "Entered >>> create_remove_script()"
    cat > $LOCAL_REMOVE_SCRIPT <<EOF
#!/bin/bash
service bushido-agent stop
rpm -e bushido-agent
rm -rf /home/bushido/
exit 0

# End script
EOF
    [[ $? -ne 0 ]] && echo Failed to create $LOCAL_REMOVE_SCRIPT 
    log Setup script $LOCAL_REMOVE_SCRIPT created with contents:
    cat $LOCAL_REMOVE_SCRIPT | log
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


function upload_script {
    log "Entered >>> upload_script($@)"
    local ip=$1
    log "Uploading to $ip"
    remote_copy $ip $LOCAL_REMOVE_SCRIPT
    ssh_user $ip "chmod +x $REMOTE_REMOVE_SCRIPT"
}

function for_each_vm_run {
    log "Entered >>> for_each_vm_run($2 $3)"
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
        log "Running '$fn $ip $fn_args' for $host"
        log "ID is $ID"

        $fn $ip "$fn_args" # TODO: CAN WE LOG THIS
    done
    ID=0
    log Finished calling $fm for each VM
}

function ip2int {
    local a b c d
    { IFS=. read a b c d; } <<< $1
    echo $(((((((a << 8) | b) << 8) | c) << 8) | d))
}


function ip2id
{
    local a b c d
    { IFS=. read a b c d; } <<< $1
    echo $(((((  b << 8) | c) << 8) | d)); 
}



function for_each_vm_run_in_bg {
    log "Entered >>> for_each_vm_run_in_bg($2 $3)"
    local vm_list="$1"
    local fn=$2
    local fn_args="$3"
    local i host ip

    local -a vms=($vm_list)

    for (( i=0; i<${#vms[@]} ; i+=2 )) ; do
        host="${vms[i]}"
        ip="${vms[i+1]}"
        ID=$(ip2id $ip)

        log "Running '$fn $ip $fn_args' for $host"
        log "ID is $ID"
        $fn $ip "$fn_args" &          # TODO: CAN WE LOG THIS
        while [ $(jobs | wc -l) -ge 20 ] ; do sleep 1 ; done
    done
    wait
    ID=0
    log Finished calling $fm for each VM
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
log Started $0 with arguments: $@
create_remove_script
get_enm_nodes

for_each_vm_run_in_bg "$VMS" upload_script 
log Running $REMOTE_REMOVE_SCRIPT on each consul members
for_each_vm_run_in_bg "$VMS" ssh_root $REMOTE_REMOVE_SCRIPT

# Cleanup 
#for_each_vm_run "$VMS" ssh_root "rm -f $REMOTE_REMOVE_SCRIPT  $REMOTE_RPM"
log $0 Completed OK
log '====================================================================================='

