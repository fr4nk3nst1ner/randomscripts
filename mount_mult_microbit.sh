#!/bin/bash
# microbit_mount.sh
# Mount and unmount Microbit devices
# Useful on linux when you have multiple microbit devices that need to be mounted 

BASEPATH="/media/$(whoami)/microbit/"
MICRO="MICROBIT"

if [ $# -eq 0 ]; then
    echo "No argument supplied. Usage: $0 [mount | unmount]"
    exit 1
fi

if [ "$1" == "--help" ]; then
    echo "Mounts or unmounts all BBC micro:bit devices"
    echo "Usage: $0 [mount | unmount]"
    exit 0
fi

# Function to create unique mountpoint based on label
create_mountpoint() {
    local label="$1"
    local mountpoint="$BASEPATH$label"
    if [ ! -d "$mountpoint" ]; then
        echo "Creating mountpoint: $mountpoint"
        mkdir -p "$mountpoint"
    fi
    echo "$mountpoint"
}

# Function to check if device is mounted
is_mounted() {
    local device="$1"
    mount | grep -q "/dev/$device"
}

# Function to unmount device
do_unmount() {
    local device="$1"
    sudo umount "/dev/$device"
}

# Find all MICROBIT devices
DEVICE_INFO=$(lsblk -o NAME,LABEL | grep "$MICRO" | awk '{print $1}')

if [ -z "$DEVICE_INFO" ]; then
    echo "No $MICRO devices found"
    exit 0
fi

# Process each device
for DEVICE in $DEVICE_INFO; do
    DEVICELABEL=$(lsblk -o NAME,LABEL | grep "$DEVICE" | awk '{print $2}')

    if [ "$DEVICELABEL" != "$MICRO" ]; then
        echo "Error: Device $DEVICE is not labeled as $MICRO"
        continue
    fi

    DEVICEPATH=$(create_mountpoint "$DEVICELABEL")
    echo "Found $MICRO, device: /dev/$DEVICE"

    # Check if the device is mounted
    if is_mounted "$DEVICE"; then
        echo "$MICRO is mounted"
        if [ "$1" == "unmount" ]; then
            # Attempt to unmount the device
            do_unmount "$DEVICE"
            if [ $? -eq 0 ]; then
                echo "Unmounted $MICRO successfully"
                # Remove mountpoint if it's empty
                rmdir "$DEVICEPATH" 2>/dev/null
            else
                echo "Failed to unmount $MICRO"
            fi
        fi
    else
        echo "$MICRO is not mounted"
        if [ "$1" == "mount" ]; then
            # Mount the device
            sudo mount "/dev/$DEVICE" "$DEVICEPATH"
            if [ $? -eq 0 ]; then
                echo "Mounted $MICRO successfully"
            else
                echo "Failed to mount $MICRO"
            fi
        fi
    fi
done

exit 0
