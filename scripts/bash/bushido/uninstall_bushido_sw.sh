#!/bin/bash


function error {
    echo $@
    exit 1
}   

[[ $(whoami) != bushido ]] && error This script must be ran as bushido

/home/bushido/components/scripts/bushido.sh stop
for r in $( rpm -qa | grep ^bushido- ); do sudo rpm -e $r; done

sudo rm -rf /home/bushido/components/*
sudo rm -rf /data/{1,2,3}/cassandra/* /log/1/cassandra/*
sudo rm -rf /elastic/nodes/* /message/{logs,zookeeper}/*

