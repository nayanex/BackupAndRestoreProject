#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="INSTALL-BUSHIDO-SOFTWARE"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

# Extract RPMs from Bushido Archive
cd /home/bushido
tar xvf bushido.tar || { error "Failed to extract bushido.tar"; exit 1; }
tar xvfz BUSHIDO*.tar.gz || { error "Failed to extract bushido.tar.gz"; exit 1; }

# Install Bushido Archive RPMs
rpm -ivh --nodeps $(<pkgs.lis) || { error "Failed to install Bushido Archive RPMs"; exit 1; }

# Install Jemalloc
rpm -ivh jemalloc.rpm || { error "Failed to install Jemalloc RPM"; exit 1; }

BUSHIDO_VERSION=`echo BUSHIDO*.tar.gz | egrep -o '[0-9]+.[0-9]+.[0-9]+'`

if [ "$BUSHIDO_VERSION" -eq "2.4.0" ]
then
    # Katana Workaround
    # The version of the Bushido rpms that we're using has an old version of katana (a component of Bushido).
    # Replace the old version of katana (Note this step should be removed when we get the next official release of Bushido).
    tar xvzf ericsson-katana.tar.gz
    mv -f ericsson/katana.jar /home/bushido/components/katana/lib/katana.jar

    # This newer version of Katana allows us to configure certain properties for it to work better with the ENM system.
    # current kata.properties
    sed -i '/profile.write.update.interval=/c\'                     /home/bushido/components/config/current/katana.properties > /dev/null
    sed -i '/katana.lastvalue.flushtime=/c\'                        /home/bushido/components/config/current/katana.properties > /dev/null

    echo "profile.write.update.interval=300"                        >> /home/bushido/components/config/current/katana.properties
    echo "katana.lastvalue.flushtime=5000"                          >> /home/bushido/components/config/current/katana.properties

    # default katana.properties
    sed -i '/profile.write.update.interval=/c\'                     /home/bushido/components/config/default/katana.properties > /dev/null
    sed -i '/katana.lastvalue.flushtime=/c\'                        /home/bushido/components/config/default/katana.properties > /dev/null

    echo "profile.write.update.interval=300"                        >> /home/bushido/components/config/default/katana.properties
    echo "katana.lastvalue.flushtime=5000"                          >> /home/bushido/components/config/default/katana.properties

    # help katana.properties
    sed -i '/katana.lastvalue.flushtime=/c\'                        /home/bushido/components/config/help/katana.properties > /dev/null
    sed -i '/profile.write.update.interval=/c\'                     /home/bushido/components/config/help/katana.properties > /dev/null

    echo "katana.lastvalue.flushtime=Map Flush Time"                >> /home/bushido/components/config/help/katana.properties
    echo "profile.write.update.interval=Profile Update Interval"    >> /home/bushido/components/config/help/katana.properties

    # vtype katana.properties
    sed -i '/katana.lastvalue.flushtime=/c\'                        /home/bushido/components/config/vtype/katana.properties > /dev/null
    sed -i '/profile.write.update.interval=/c\'                     /home/bushido/components/config/vtype/katana.properties > /dev/null

    echo "katana.lastvalue.flushtime=numeric"                       >> /home/bushido/components/config/vtype/katana.properties
    echo "profile.write.update.interval=numeric"                    >> /home/bushido/components/config/vtype/katana.properties

    # config config.properties
    sed -i '/profile.write.update.interval=/c\'                     /home/bushido/components/config/katana.properties > /dev/null
    sed -i '/katana.lastvalue.flushtime=/c\'                        /home/bushido/components/config/katana.properties > /dev/null

    echo "profile.write.update.interval=300"                        >> /home/bushido/components/config/katana.properties
    echo "katana.lastvalue.flushtime=5000"                          >> /home/bushido/components/config/katana.properties
fi

# Enable/Disable Services required for Bushido
systemctl enable ntpd.service
systemctl disable firewalld
systemctl mask firewalld
systemctl enable iptables.service
sysctl -p /etc/sysctl.d/98-bushido.conf

# Setup keys
cat /home/cloud-user/.ssh/authorized_keys >> /home/bushido/.ssh/authorized_keys

# Start Ronin for cluster configuration
/home/bushido/components/scripts/ronin.sh start

# Backup and cleanup Bushido Server RPMs, TODO: do we need this?!?!?!

cd /home/bushido
mkdir ROLLBACK
mv *rpm *lis ROLLBACK
cp /home/bushido/components/katana/lib/katana.jar ROLLBACK
rm -rf *tar *tar.gz ericsson

echo "$(date) Install bushido_server_$BUSHIDO_VERSION" >> /etc/bushido_version