#!/bin/bash

SCRIPT_NAME=$(basename ${0})
LOG_TAG="CONFIGURE-EXTRA-VOLUMES"
ENM_UTILS=/opt/ericsson/enm-configuration/etc/enm_utils.lib
[ ! -f ${ENM_UTILS} ] && { logger "ERROR ${ENM_UTILS} doesn't exist"; exit 1; }
source ${ENM_UTILS}

# Create Partition for Each Volume
for disk in b c d e f g ; do
    echo 'n p 1   t 8e w ' | tr ' ' '\n' | fdisk /dev/vd${disk}
done
# echo sends commands (with tr replacing spaces for newlines),
# so: n=new p=primary 1=1st partition '\n'=default start '\n'=default end t=toggle type 8e=LVM type w=write changes

# For each partition device created, make a corresponding LVM Physical Volume:
pvcreate /dev/vdb1 || { error "Failed to create LVM Physical Volume vdb1"; exit 1; }
pvcreate /dev/vdc1 || { error "Failed to create LVM Physical Volume vdc1"; exit 1; }
pvcreate /dev/vdd1 || { error "Failed to create LVM Physical Volume vdd1"; exit 1; }
pvcreate /dev/vde1 || { error "Failed to create LVM Physical Volume vde1"; exit 1; }
pvcreate /dev/vdf1 || { error "Failed to create LVM Physical Volume vdf1"; exit 1; }
pvcreate /dev/vdg1 || { error "Failed to create LVM Physical Volume vdg1"; exit 1; }

# Create LVM Volume Group for Each LVM Physical Volume
vgcreate VolData1 /dev/vdb1 || { error "Failed to create LVM Volume Group VolData1 /dev/vdb1"; exit 1; }
vgcreate VolData2 /dev/vdc1 || { error "Failed to create LVM Volume Group VolData2 /dev/vdc1"; exit 1; }
vgcreate VolData3 /dev/vdd1 || { error "Failed to create LVM Volume Group VolData3 /dev/vdd1"; exit 1; }
vgcreate VolLog /dev/vde1 || { error "Failed to create LVM Volume Group VolLog /dev/vde1"; exit 1; }
vgcreate VolMsg /dev/vdf1 || { error "Failed to create LVM Volume Group VolMsg /dev/vdf1"; exit 1; }
vgcreate VolElastic /dev/vdg1 || { error "Failed to create LVM Volume Group VolElastic /dev/vdg1"; exit 1; }

# Create Logical Volume on each Volume Group
lvcreate -l +100%FREE -n LVData1 VolData1 || { error "Failed to create Logical Volume LVData1"; exit 1; }
lvcreate -l +100%FREE -n LVData2 VolData2 || { error "Failed to create Logical Volume LVData2"; exit 1; }
lvcreate -l +100%FREE -n LVData3 VolData3 || { error "Failed to create Logical Volume LVData3"; exit 1; }
lvcreate -l +100%FREE -n LVLog VolLog || { error "Failed to create Logical Volume LVLog"; exit 1; }
lvcreate -l +100%FREE -n LVMsg VolMsg || { error "Failed to create Logical Volume LVMsg"; exit 1; }
lvcreate -l +100%FREE -n LVElastic VolElastic || { error "Failed to create Logical Volume LVElastic"; exit 1; }

# Create File System on Each Logical Volume
mkfs.xfs -f  /dev/VolData1/LVData1 || { error "Failed to create File System on LVData1"; exit 1; }
mkfs.xfs -f /dev/VolData2/LVData2 || { error "Failed to create File System on LVData2"; exit 1; }
mkfs.xfs -f /dev/VolData3/LVData3 || { error "Failed to create File System on LVData3"; exit 1; }
mkfs.xfs -f /dev/VolLog/LVLog || { error "Failed to create File System on LVLog"; exit 1; }
mkfs.xfs -f /dev/VolMsg/LVMsg || { error "Failed to create File System on LVMsg"; exit 1; }
mkfs.xfs -f /dev/VolElastic/LVElastic || { error "Failed to create File System on LVElastic"; exit 1; }

# Mount Logical Volumes and Create Bushido Directories
mkdir -p /data/{1,2,3} /log /elastic /message
chown -Rf bushido:bushido  /data/ /log /elastic /message

# Add mount entries in fstab:
echo "/dev/mapper/VolData1-LVData1               /data/1  xfs  defaults 1 2 " >> /etc/fstab
echo "/dev/mapper/VolData2-LVData2               /data/2  xfs  defaults 1 2 " >> /etc/fstab
echo "/dev/mapper/VolData3-LVData3               /data/3  xfs  defaults 1 2 " >> /etc/fstab
echo "/dev/mapper/VolElastic-LVElastic           /elastic xfs  defaults 1 2 " >> /etc/fstab
echo "/dev/mapper/VolLog-LVLog                   /log     xfs  defaults 1 2 " >> /etc/fstab
echo "/dev/mapper/VolMsg-LVMsg                   /message xfs  defaults 1 2 " >> /etc/fstab
mount -a