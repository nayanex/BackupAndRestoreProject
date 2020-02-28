#!/bin/bash
 
# keystonerc exports use staging for all tenancies - this is ok
export OS_USERNAME=enmstaging04
export OS_PASSWORD=12shrootStaging
export OS_AUTH_URL=https://10.2.63.251:13000/v3
export OS_PROJECT_NAME=ENM_Staging_04


function usage {
    local ret=${1:0}
    echo "Usage: $0 [--agent=VERSION] [--server=VERSION]"
    echo "Download Bushido server or agent from Glance."
    echo "Valid versions for the agent are, 1921, 1929, 1946"
    echo "Valid versions for the server are 2.4.0 and  2.4.1"
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




function get_token {
    curl --insecure -i -H "Content-Type: application/json" -d '
    { "auth": {
        "identity": {
          "methods": ["password"],
          "password": {
            "user": {
              "name": "'${OS_USERNAME}'",
              "domain": { "id": "default" },
              "password": "'${OS_PASSWORD}'"
            }  
          }  
        },
        "scope": {
          "project": {
            "name": "'${OS_PROJECT_NAME}'",
            "domain": { "id": "default" }
          }  
        }  
      }
    }' "${OS_AUTH_URL}/auth/tokens" 2>/dev/null  | awk '/X-Subject-Token/ {print $2}' | sed  's/\r//'
}

function check_agent_version {
    [[ "$1" =~ ^(1921|1929|1946)$ ]] || error "Agent version $1 is not valid"
} 



function check_server_version {
    [[ "$1" =~ ^(2.4.0|2.4.1)$ ]] || errror "Server version $1 is not valid"
}


function download {
    local path=$1
    local name=$2
    curl --insecure -s -H "X-Auth-Token: $OS_TOKEN" $URL/$path > $name || error Failed to download $name
}


function download_agent {
    local version=$1
    local path=${AGENT_PATH[$1]}
    local md5=${AGENT_MD5[$1]}        
    local name=/tmp/agentpackager-${version}.tar.gz
    local file_cksum
    download $path $name
    file_cksum=$(md5sum $name | awk ' { print $1 } ')
    [[ -n $file_cksum ]] || error Failed to get checksum for $file
    [[ $file_cksum == $md5 ]]  || error Bad checksum for $file
    log $name downloaded successfully
}

function download_server {
    local version=$1
    local path=${SERVER_PATH[$1]}
    local md5=${SERVER_MD5[$1]}
    local name=/tmp/bushido.tar
    local jemalloc=/tmp/jemalloc.rpm
    local file_cksum

    download $JEMALLOC_PATH $jemalloc
    file_cksum=$(md5sum $jemalloc | awk ' { print $1 } ')
    [[ -n $file_cksum ]] || error Failed to get checksum for $jemalloc
    [[ $file_cksum == $JEMALLOC_MD5 ]]  || error Bad checksum for $jemalloc
    log $jemalloc downloaded successfully

    download $path $name
    file_cksum=$(md5sum $name | awk ' { print $1 } ')
    [[ -n $file_cksum ]] || error Failed to get checksum for $file
    [[ $file_cksum == $md5 ]]  || error Bad checksum for $file
    log $name downloaded successfully
}


LOG=${0}.log


declare -A SERVER_PATH=( [2.4.0]=/v2/images/5e8f1bfb-513a-4f50-96d9-3baccc43c126/file
                         [2.4.1]=/v2/images/fb08c6e6-e08b-4d23-9410-5ce648ad66a0/file )

declare -A SERVER_MD5=( [2.4.0]=74d30cd2bf3b70221f9914ed74001076
                        [2.4.1]=35c71e05a59ee5f5680ead056f2d97c0 )

declare -A AGENT_PATH=( [1921]=/v2/images/53c1cb3b-13e7-4151-959c-1e3392520e42/file
                        [1929]=/v2/images/b4b0cb21-8afe-4d43-886c-887aa3f40746/file
                        [1946]=/v2/images/60e38ab8-4010-420a-9b2c-2420f40ccda1/file )

declare -A AGENT_MD5=( [1921]=f71984554e5fe532895d4c6c0e9954d5
                       [1929]=c5eaeef4990387eb20b814e132489268
                       [1946]=88d27fe82189756aa0ac9c32604d0521 )

JEMALLOC_PATH=/v2/images/6a26269b-f9fa-4b21-909b-acaa654d89a2/file
JEMALLOC_MD5=b3a15b12ce051c18948e47deeeeb7849

DOWNLOAD_AGENT=false
DOWNLOAD_SERVER=false

URL=https://10.2.63.251:13292

#     echo "Usage: $0 [--agent=VERSION] [--server=VERSION]"
# [[ "$VM_FILE" =~ --whitelist* ]] && WHITELIST=true

[[ $1 =~ .*-h.* ]] && usage
[[ -n "$1" ]] || usage 1
[[ -n "$3" ]] && usage 1


while [[ -n "$1" ]] ; do
    if [[ "$1" =~ --agent*  ]] ; then
        AGENT_VERSION=$(cut -d= -f2- <<< $1)
        DOWNLOAD_AGENT=true 
    elif [[ "$1" =~ --server*  ]] ; then
        SERVER_VERSION=$(cut -d= -f2- <<< $1)
        DOWNLOAD_SERVER=true
    else
        usage 1
    fi
    shift
done

OS_TOKEN=$(get_token)

if $DOWNLOAD_AGENT ; then
    check_agent_version $AGENT_VERSION
    download_agent $AGENT_VERSION
fi

if $DOWNLOAD_SERVER ; then
    check_server_version $SERVER_VERSION
    download_server $SERVER_VERSION
fi

