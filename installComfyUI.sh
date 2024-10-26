#!/bin/bash

# clone repo
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# create conda env
conda activate comfyui-env
conda create -n comfyui-env python=3.10

# clone repo
git clone https://github.com/comfyanonymous/ComfyUI.git

# clone custom nodes
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git custom_nodes/ComfyUI-VideoHelperSuite
git clone https://github.com/cubiq/ComfyUI_essentials.git custom_nodes/ComfyUI_essentials.git
git clone https://github.com/kijai/ComfyUI-KJNodes.git custom_nodes/ComfyUI-KJNodes
git clone https://github.com/kijai/ComfyUI-LivePortraitKJ.git custom_nodes/ComfyUI-LivePortraitKJ
git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager


# pull required models
huggingface-cli download Kijai/LivePortrait_safetensors appearance_feature_extractor.safetensors --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors landmark.onnx  --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors landmark_model.pth --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors motion_extractor.safetensors --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors spade_generator.safetensors --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors stitching_retargeting_module.safetensors --local-dir /home/jstines/ComfyUI/models/liveportrait/
huggingface-cli download Kijai/LivePortrait_safetensors warping_module.safetensors --local-dir /home/jstines/ComfyUI/models/liveportrait/

# install required pip modules
pip install -r requirements.txt
pip install -r custom_nodes/ComfyUI-LivePortraitKJ/requirements.txt
pip install imageio_ffmpeg rich insightface mediapipe onnxruntime opencv-python-headless pykalman opencv-python numba

# Settings tweaks for image to video

# 1. use LivePortrait Load FaceAlignmentCropper node with blazeback_back_camera and torch_cuda
# 2. set face detector dtype to fp32 in LivePortrait Load FaceAlignmentCropper node
# 3. set frame rate to 32 in Video Combine node
# 4. increase frame_load_cap value to a higher number  (e.g., 270 for 9 seconds) to allow longer videos
# 5. to prevent memory crashes, set force_size in Load Video Upload node to 512 for both custom_height and custom_width

export myip=127.0.0.1

python main.py --listen $myip
