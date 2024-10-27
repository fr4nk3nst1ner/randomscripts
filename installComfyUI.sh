#!/bin/bash

# Clone necessary repos
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Create and activate Conda environment
conda create -n comfyui-env python=3.10 -y
conda activate comfyui-env

# Clone custom nodes
declare -A custom_nodes=(
  ["ComfyUI-VideoHelperSuite"]="Kosinkadink/ComfyUI-VideoHelperSuite"
  ["ComfyUI_essentials"]="cubiq/ComfyUI_essentials"
  ["ComfyUI-KJNodes"]="kijai/ComfyUI-KJNodes"
  ["ComfyUI-LivePortraitKJ"]="kijai/ComfyUI-LivePortraitKJ"
  ["ComfyUI-Manager"]="ltdrdata/ComfyUI-Manager"
)

for node in "${!custom_nodes[@]}"; do
  git clone "https://github.com/${custom_nodes[$node]}.git" "custom_nodes/$node"
done

# Pull required models using Hugging Face
model_dir="/home/jstines/ComfyUI/models/liveportrait/"
model_files=(
  "appearance_feature_extractor.safetensors"
  "landmark.onnx"
  "landmark_model.pth"
  "motion_extractor.safetensors"
  "spade_generator.safetensors"
  "stitching_retargeting_module.safetensors"
  "warping_module.safetensors"
)

for model in "${model_files[@]}"; do
  huggingface-cli download Kijai/LivePortrait_safetensors "$model" --local-dir "$model_dir"
done

# Install required dependencies
pip install -r requirements.txt
pip install -r custom_nodes/ComfyUI-LivePortraitKJ/requirements.txt
pip install imageio_ffmpeg rich insightface mediapipe onnxruntime opencv-python-headless pykalman opencv-python numba

# Configuration for image-to-video processing
export myip=127.0.0.1

# Settings tweaks
# 1. Use LivePortrait Load FaceAlignmentCropper node with `blazeback_back_camera` and `torch_cuda`.
# 2. Set face detector dtype to `fp32` in LivePortrait Load FaceAlignmentCropper node.
# 3. Set frame rate to 32 in Video Combine node.
# 4. Increase `frame_load_cap` to a higher value (e.g., 270 for 9 seconds).
# 5. To prevent memory crashes, set force_size in Load Video Upload node to 512 for both `custom_height` and `custom_width`.

# Run ComfyUI
python main.py --listen $myip
