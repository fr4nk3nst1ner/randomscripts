#!/bin/bash

# OS: Ubuntu
# Script that performs the following:
# 1. Create UBIFS image 
# 2. Embeds the UBIFS into a UBI image 
# 3. Mounts the image 

# install requirements 
sudo apt install mtd-utils

# Ensure no UBI devices are attached
sudo ubidetach /dev/ubi_ctrl -m 0 > /dev/null 2>&1

# Unload UBI and UBIFS modules if loaded
sudo modprobe -r ubi ubifs > /dev/null 2>&1

# Unload and reload NAND simulator with correct parameters
sudo modprobe -r nandsim > /dev/null 2>&1
sudo modprobe nandsim first_id_byte=0x20 second_id_byte=0xaa third_id_byte=0x00 fourth_id_byte=0x15

# Reload UBI module
sudo modprobe ubi

# Create a test directory and a sample file
mkdir -p test_dir
echo "This is a test file" > test_dir/test_file.txt

# Create the UBIFS image with correct parameters
mkfs.ubifs -r test_dir -m 2048 -e 129024 -c 2048 -o test_ubifs.img

# Create a UBI configuration file
cat <<EOF > ubinize.cfg
[test_volume]
mode=ubi
image=test_ubifs.img
vol_id=0
vol_size=246MiB
vol_type=dynamic
vol_name=test_volume
vol_flags=autoresize
EOF

# Create the UBI image
ubinize -o test_ubi.img -m 2048 -p 128KiB -s 512 ubinize.cfg

# Format the mtd device with the UBI image
sudo ubiformat /dev/mtd0 -f test_ubi.img

# Attach the UBI image
sudo ubiattach /dev/ubi_ctrl -m 0

# Verify the UBI device and volume
sudo ubinfo -d 0
sudo ubinfo -d 0 -a

# Mount the UBIFS volume
sudo umount /mnt
sudo mount -t ubifs ubi0:test_volume /mnt

# Access the file
ls /mnt
cat /mnt/test_file.txt
