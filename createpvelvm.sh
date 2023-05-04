#!/bin/bash

# script to create a lvm template using cloud-init for proxmox

wget https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64-disk-kvm.img
qm create 8200 --memory 8192 --name 2ubuntu-cloud --net0 virtio,bridge=vmbr0
qm importdisk 8200 focal-server-cloudimg-amd64.img one_nvme
qm set 8200 --ide2 one_nvme
qm set 8200 --ide2 one_nvme:cloudinit
qm set 8200 --boot c --bootdisk scsi0
qm set 8200 --serial0 socket --vga serial0
