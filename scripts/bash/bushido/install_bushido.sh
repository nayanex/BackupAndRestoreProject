#!/bin/bash


function error {
    echo $@
    exit 1
}

[[ $(whoami) != bushido ]] && error This script must be ran as bushido


#INSTALL_DIR=/home/bushido/UPGRADE
#INSTALL_DIR=/home/bushido/ROLLBACK

INSTALL_DIR=$1
[[ -n "$1" ]] || { echo Usage: $0 <Directory containing bushido.tar> ; exit 1 }
[[ -d "$1" ]] || { echo Usage: $0 <Directory containing bushido.tar> ; exit 1 }


# Create Bushido Directories
mkdir -p  /data/{1,2,3}/cassandra /log/1/cassandra
mkdir -p  /elastic/nodes /message/{logs,zookeeper}

# Extract and install software
cd $INSTALL_DIR
sudo tar xvf bushido.tar
sudo rpm -ivh --nodeps $(<pkgs.lis)
sudo rpm -ivh jemalloc.rpm
sudo rm -f bushido.tar
cd -

# Set permissions
sudo chown -R bushido:bushido /home/bushido/

# Configure services
sudo systemctl enable ntpd.service
sudo systemctl disable firewalld
sudo systemctl mask firewalld
sudo systemctl enable iptables.service
sudo sysctl -p /etc/sysctl.d/98-bushido.conf

# Setup public key for Bushido
#sudo -u bushido mkdir -p -m 700 /home/bushido/.ssh
mkdir -p -m 700 /home/bushido/.ssh


sudo cat /home/cloud-user/.ssh/authorized_keys >> /home/bushido/.ssh/authorized_keys
chown bushido:bushido /home/bushido/.ssh/authorized_keys
chmod 700 /home/bushido/.ssh/authorized_keys

# Start Ronin for cluster configuration
#sudo -u bushido /home/bushido/components/scripts/ronin.sh start
/home/bushido/components/scripts/ronin.sh start



