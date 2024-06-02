#!/bin/bash

# source: https://medium.com/@Null0xFF/setting-up-the-bladerf-2-0-micro-xa4-with-gnu-radio-on-ubuntu-20-04-f36fce4dd47c

# install required packages
sudo apt-get update
sudo apt install git cmake build-essential libusb-1.0-0-dev libusb-1.0-0 build-essential cmake
libncurses5-dev libtecla1 libtecla1-dev pkg-config

# clone the repo
git clone https://github.com/Nuand/bladeRF.git /opt/bladeRF

# grab the latest FPGA for bladerf xA4 and firmware image
wget https://www.nuand.com/fpga/hostedxA4-latest.rbf
wget https://www.nuand.com/fx3/bladeRF_fw_latest.img

# build the bladerf source
cd bladeRF/host/
mkdir build
cmake ../
make
sudo make install
sudo ldconfig

# plug in bladerf and ensure everything works
bladeRF-cli -p

# update the firmware
bladeRF-cli -f bladeRF_fw_latest.img

# load the fpga
bladeRF-cli -l hostedxA4-latest.rbf

# setup gnu radio and gr-bladeRF
sudo add-apt-repository ppa:gnuradio/gnuradio-releases-3.9
sudo apt-get update
sudo apt-get install gnuradio python3-packaging

# install gr-osmosdr
sudo apt-get install gr-osmosdr

# install the gr-bladeRF blocks for GNU Radio
git clone https://github.com/Nuand/gr-bladeRF.git
cd gr-bladeRF
mkdir build
cd build
cmake ..
make -j4
sudo make install

# Set the LD_LIBRARY_PATH path
LD_LIBRARY_PATH=/usr/local/lib bladeRF-cli -p
sudo ldconfig

# Test with FM receiver
gnuradio-companion gr-bladeRF/apps/fm_receiver.grc

# Before we finish, you will need to set the FPGA Image path for the bladeRF source and sink.
# This ensures it loads the FPGA image onto the SDR if you ever power the device down as it will not store the image.
# https://miro.medium.com/v2/resize:fit:1196/format:webp/1*qDry9Ey48BROu-h0qYbYUQ.png
