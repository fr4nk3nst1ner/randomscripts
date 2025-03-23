#!/bin/bash
set -e


# Script for building fuzzware for macos
# 1. Disables FPU checks: The CMSIS header file is modified to skip FPU-related checks that fail on macOS.
# 2. Adding compiler flags: Special compiler flags are added that instruct clang to avoid generating floating-point instructions and to use software emulation for floating-point operations when necessary.
# 3. Creating a dedicated build script: The new script handles the installation of dependencies and builds the project with the correct settings for macOS.


echo "[INFO] Building Fuzzware on macOS"

# Install required dependencies if brew is available
if command -v brew >/dev/null 2>&1; then
  echo "[INFO] Installing dependencies via Homebrew..."
  brew install python3 libusb cmake
else
  echo "[WARN] Homebrew not found. Please install required dependencies manually."
  echo "Required: python3, libusb, cmake"
fi

# Setup python virtualenv
echo "[INFO] Setting up Python virtualenv..."
python3 -m pip install --user virtualenv
python3 -m virtualenv venv
source venv/bin/activate

# Install Python dependencies
echo "[INFO] Installing Python dependencies..."
pip install -r emulator/requirements.txt -r pipeline/requirements.txt

# Build AFL if needed
echo "[INFO] Building AFL..."
cd emulator
AFL_NO_X86=1 ./get_afl.sh

# Build unicorn
echo "[INFO] Building Unicorn..."
cd unicorn/fuzzware-unicorn
UNICORN_QEMU_FLAGS="--python=$(which python)" ./make.sh
cd ../..

# Build harness
echo "[INFO] Building harness..."
make -C harness/fuzzware_harness/native clean all

# Install Python packages
echo "[INFO] Installing Python packages..."
pip install -e harness
pip install -e fuzzer

cd ..

# Setup modeling virtualenv
echo "[INFO] Setting up modeling virtualenv..."
python3 -m virtualenv modeling-venv
source modeling-venv/bin/activate
pip install -r modeling/requirements.txt
pip install -e modeling

echo "[INFO] Build completed successfully!"
echo "To run Fuzzware, activate the virtualenv with:"
echo "  source venv/bin/activate"
