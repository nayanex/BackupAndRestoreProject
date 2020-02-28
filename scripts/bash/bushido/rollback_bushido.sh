#!/bin/bash

. ~/components/config/bushido.env

BKDIR=~/ROLLBACK/PRE_UPGRADE_CFG
RBDIR=~/ROLLBACK

bushido.sh stop

cd $HOME

rsync -av components/config components/certs \
          components/jdk*/jre/lib/security/cacerts \
          components/apache-cassandra-*/conf/cassandra.yaml \
          components/kafka_*/config/zookeeper.properties \
          components/kafka_*/config/server.properties  $BKDIR

cd $RBDIR
sudo rpm -Uvh –force --nodeps $(egrep -v 'bushido.*(mule|java|subversion)' pkgs.lis)
sudo rpm -e bushido-mule
sudo rpm -ivh --nodeps $(egrep 'bushido.*mule' pkgs.lis)

