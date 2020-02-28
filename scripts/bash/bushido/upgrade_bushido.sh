#!/bin/bash

. ~/components/config/bushido.env

BKDIR=~/ROLLBACK/PRE_UPGRADE_CFG
UGDIR=~/UPGRADE

BUSHIDO_IP=$(awk -F"=" '/server.ipaddress/{print $2}' $CONFIG | tr -d '[:space:]')
declare -a ES_MAPPINGS=("auditinfo" "alertinfo" "annotationinfo")

bushido.sh stop
[ -d $BKDIR ] || mkdir -p $BKDIR
cd $HOME
rsync -av components/config components/certs components/jdk*/jre/lib/security/cacerts \
          components/apache-cassandra-*/conf/cassandra.yaml \
          components/kafka_*/config/zookeeper.properties \
          components/kafka_*/config/server.properties  $BKDIR/


cd $UGDIR
sudo rpm -Uvh --nodeps $(egrep -v 'bushido.*(mule|java|subversion)' pkgs.lis)
sudo rpm -e bushido-mule
sudo rpm -ivh --nodeps $(egrep 'bushido.*mule' pkgs.lis)
config_es_cluster.sh fix 1

elastic.sh start
sleep 15
for ES_MAPPING in ${ES_MAPPINGS[@]} ; do
     ES_SCHEMA="${COMPONENTS}/schema/es_${ES_MAPPING}.json"
     [ -f "$ES_SCHEMA" ] && \
     curl -XPUT http://${BUSHIDO_IP}:9200/_template/${ES_MAPPING} \
          -H 'Content-Type: application/json' -d "$(< $ES_SCHEMA)"
done

