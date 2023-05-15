#!/bin/bash

# script to create a pve vm template using cloud-init for proxmox

# retrieve ubuntu image 
wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64-disk-kvm.img

# create our disk id and assign other parameters 
qm create 8200 --memory 8192 --name 2ubuntu-cloud --net0 virtio,bridge=vmbr0

# import the disk so we can use it as an img 
qm importdisk 8200 focal-server-cloudimg-amd64.img local-lvm

# create the actual image 
qm set 8200 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-8200-disk-0

# create our cloud-init drive 
qm set 8200 --ide2 local-lvm:cloudinit

# make drive bootable, speed up boot times 
qm set 8200 --boot c --bootdisk scsi0

# enable serial console 
qm set 8200 --serial0 socket --vga serial0
