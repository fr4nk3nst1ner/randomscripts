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



# Steps for doing this with Kali 


# step 1: download iso 
wget https://cdimage.kali.org/kali-2024.1/kali-linux-2024.1-qemu-amd64.7z
7z e kali-linux-2024.1-qemu-amd64.7z

# step 2: scp qcow file to proxmox 
scp kali-linux-2024.1-qemu-amd64.qcow2 proxmox:/var/lib/vz/template/iso/

# step 3: import the image 
ssh proxmox

qm create 8400 --memory 8192 --name kali --net0 virtio,bridge=vmbr0
qm importdisk 8400 /var/lib/vz/template/iso/kali-linux-2024.1-qemu-amd64.qcow2 truenas
qm set 8400 --scsihw virtio-scsi-pci --scsi0 truenas:8400/vm-8400-disk-0.raw
qm set 8400 --ide2 truenas:cloudinit
qm set 8400 --boot c --bootdisk scsi0
qm set 8400 --serial0 socket --vga serial0


