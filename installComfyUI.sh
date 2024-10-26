#!/bin/bash

# script for installation of ComfyUI on Ubuntu 

git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
conda create -n comfyui-env python=3.10
conda activate comfyui-env
pip install -r requirements.txt
pip install imageio_ffmpeg rich insightface mediapipe onnxruntime opencv-python-headless pykalman opencv-python
git clone https://github.com/kijai/ComfyUI-KJNodes.git custom_nodes/ComfyUI-KJNodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git custom_nodes/ComfyUI-VideoHelperSuite
git clone https://github.com/cubiq/ComfyUI_essentials.git custom_nodes/ComfyUI_essentials.git
git clone https://github.com/kijai/ComfyUI-LivePortraitKJ.git custom_nodes/ComfyUI-LivePortraitKJ
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager
pip install -r custom_nodes/ComfyUI-LivePortraitKJ/requirements.txt

export myip=127.0.0.1

python main.py --listen $myip
