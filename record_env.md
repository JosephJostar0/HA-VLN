# 🚀 Quick Start (Updated for Ubuntu 24.04 & Modern Linux)

The original repositories rely on older dependencies (Python 3.7, CUDA 11.1). If you are on a modern Linux distribution (like Ubuntu 22.04 or 24.04), strictly following the steps below will prevent legacy compilation errors, dependency hell, and C++ compiler mismatches.

**Note:** We highly recommend using `mamba` instead of `conda` for resolving these older environments, as it is significantly faster.

## 1. Install System Dependencies

First, install the required graphics and encryption libraries on your host machine. We use `libgl1` (replacing the deprecated `libgl1-mesa-glx`) and `libcrypt-dev` (required for compiling `lmdb` later).

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends libjpeg-dev libglm-dev libgl1 libegl1-mesa-dev mesa-utils xorg-dev freeglut3-dev libcrypt-dev
```

## 2. Clone the Repository & Create the Environment

Clone the HA-VLN repo and create an isolated environment. **Crucial:** We inject older C/C++ compilers (gcc 9) directly into the Conda environment to avoid conflicts with your system's modern compilers.

```bash
git clone https://github.com/F1y1113/HA-VLN.git
cd HA-VLN

# Create environment with locked legacy compilers
mamba create -n havlnce python=3.7 gcc_linux-64=9 gxx_linux-64=9 cudatoolkit=11.1 -c conda-forge -y
conda activate havlnce
```

## 3. Setup PyTorch & Full CUDA Toolkit

To compile custom CUDA extensions later, the basic cudatoolkit is not enough. We need the full developer toolkit to get the `nvcc` compiler.

```bash
# Install full CUDA toolkit (contains nvcc)
mamba install -c conda-forge cudatoolkit-dev=11.1.1 -y

# Export CUDA_HOME to point inside the conda environment
export CUDA_HOME=$CONDA_PREFIX

# Install PyTorch
pip install torch==1.9.1+cu111 torchvision==0.10.1+cu111 -f https://download.pytorch.org/whl/torch_stable.html
```

## 4. Install Habitat-Sim and Habitat-Lab

We use the pre-compiled binary for habitat-sim to save time. For habitat-lab, we pre-install `msgpack` to bypass a known build error with older versions of `setuptools`.

```bash
# 1. Install Habitat-Sim (Headless)
mamba install -c aihabitat -c conda-forge habitat-sim=0.1.7 headless -y

# 2. Clone and Install Habitat-Lab
git clone --branch v0.1.7 https://github.com/facebookresearch/habitat-lab.git
cd habitat-lab
pip install msgpack  # Pre-install to fix pyproject.toml parsing errors
pip install -r requirements.txt
pip install -r habitat_baselines/rl/requirements.txt
python setup.py develop --all
cd ..
```

## 5. Install GroundingDINO (With Dependency Fixes)

This step requires compiling older CUDA code against modern dependencies. We must lock several Python packages to their last Python 3.7 compatible versions and patch a Linux kernel header inside Conda to prevent `nvcc` crashes.

```bash
cd HASimulator
git clone https://github.com/IDEA-Research/GroundingDINO.git
cd GroundingDINO/

# 1. Lock dependencies to prevent Rust/puccinialin build errors
pip install "safetensors==0.3.1" "huggingface-hub==0.16.4" "tokenizers==0.13.3" "transformers==4.30.2" "timm==0.9.2"

# 2. Fix the supervision version requirement
sed -i 's/supervision.*/supervision==0.11.1/g' requirements.txt

# 3. Patch the conda sysroot types.h to prevent __int128 nvcc compilation errors
SYSROOT_TYPES="$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot/usr/include/linux/types.h"
chmod +w $SYSROOT_TYPES
sed -i 's/typedef __signed__ __int128/\/\/ typedef __signed__ __int128/g' $SYSROOT_TYPES
sed -i 's/typedef unsigned __int128/\/\/ typedef unsigned __int128/g' $SYSROOT_TYPES

# 4. Install build accelerator and compile GroundingDINO
pip install ninja
pip install -e .

# 5. Download pre-trained weights
mkdir weights
cd weights
wget -q https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
cd ../../../
```
