#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="CREATE-DATA-DIRECTORIES"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

# Create Bushido Data Directories in Mount Points
mkdir -p  /data/{1,2,3}/cassandra /log/1/cassandra
mkdir -p  /elastic/nodes /message/{logs,zookeeper}
chown -R bushido:bushido /data /log /elastic /message