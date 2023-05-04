#!/bin/bash

# script to create a pve vm template using cloud-init for proxmox

wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64-disk-kvm.img
qm create 8200 --memory 8192 --name 2ubuntu-cloud --net0 virtio,bridge=vmbr0
qm importdisk 8200 focal-server-cloudimg-amd64.img local-lvm
qm set 8200 --ide2 local-lvm:cloudinit
qm set 8200 --boot c --bootdisk scsi0
qm set 8200 --serial0 socket --vga serial0
