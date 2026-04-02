# Quick Start

The original repositories require Python 3.7 and CUDA 11.1. The following steps address compatibility issues when running on modern Linux distributions like Ubuntu 22.04 or 24.04.

## 1. Install System Dependencies

Install the required graphics and encryption libraries. This replaces the deprecated `libgl1-mesa-glx` with `libgl1` and adds `libcrypt-dev` for `lmdb` compilation.

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends libjpeg-dev libglm-dev libgl1 libegl1-mesa-dev mesa-utils xorg-dev freeglut3-dev libcrypt-dev unzip
```

## 2. Clone the Repository & Create the Environment

Clone the HA-VLN repository and create a Conda environment. This setup injects GCC 9 and GXX 9 directly into the environment to ensure compatibility with the project's requirements and avoid conflicts with modern system compilers.

```bash
git clone https://github.com/F1y1113/HA-VLN.git
cd HA-VLN

# Create environment with specific compiler and Python versions
conda create -n havlnce python=3.7 gcc_linux-64=9 gxx_linux-64=9 cudatoolkit=11.1 -c conda-forge -y
conda activate havlnce
```

## 3. Setup PyTorch & CUDA Toolkit

Install the full CUDA development toolkit to obtain the `nvcc` compiler required for custom extensions.

```bash
# Install CUDA toolkit development tools
conda install -c conda-forge cudatoolkit-dev=11.1.1 -y

# Set CUDA_HOME to the conda environment path
export CUDA_HOME=$CONDA_PREFIX

# Install PyTorch
pip install torch==1.9.1+cu111 torchvision==0.10.1+cu111 -f https://download.pytorch.org/whl/torch_stable.html
```

## 4. Install Habitat-Sim and Habitat-Lab

Install the pre-compiled binary for `habitat-sim`. For `habitat-lab`, `msgpack` is installed first, and the `torch` requirement is removed from the configuration to prevent version conflicts.

```bash
# 1. Install Habitat-Sim (Headless)
conda install -c aihabitat -c conda-forge habitat-sim=0.1.7 headless -y

# 2. Clone and Install Habitat-Lab
git clone --branch v0.1.7 https://github.com/facebookresearch/habitat-lab.git
cd habitat-lab
pip install msgpack
pip install -r requirements.txt
sed -i '/torch/d' habitat_baselines/rl/requirements.txt
pip install -r habitat_baselines/rl/requirements.txt
conda install -c conda-forge libxcrypt -y
python setup.py develop --all
cd ..
```

## 5. Install GroundingDINO

This step involves compiling CUDA code with specific Python package versions. It includes a modification to a Conda system header to resolve compilation errors related to `__int128`.

```bash
cd HASimulator
git clone https://github.com/IDEA-Research/GroundingDINO.git
cd GroundingDINO/

# 1. Install specific dependency versions
pip install "safetensors==0.3.1" "huggingface-hub==0.16.4" "tokenizers==0.13.3" "transformers==4.30.2" "timm==0.9.2"

# 2. Update supervision version
sed -i 's/supervision.*/supervision==0.11.1/g' requirements.txt

# 3. Patch types.h in the conda sysroot
SYSROOT_TYPES="$CONDA_PREFIX/x86_64-conda-linux-gnu/sysroot/usr/include/linux/types.h"
chmod +w $SYSROOT_TYPES
sed -i 's/typedef __signed__ __int128/\/\/ typedef __signed__ __int128/g' $SYSROOT_TYPES
sed -i 's/typedef unsigned __int128/\/\/ typedef unsigned __int128/g' $SYSROOT_TYPES

# 4. Install ninja and compile GroundingDINO
pip install ninja
pip install -e .

# 5. Download weights
mkdir weights
cd weights
wget -q https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth
cd ../../../
```

## 6. Install Agent Requirements

Remove `torch` and `tensorflow` from the requirements file before installation to maintain the environment's specified versions.

```bash
sed -i '/torch/d' agent/VLN-CE/requirements.txt
sed -i '/tensorflow/d' agent/VLN-CE/requirements.txt
pip install -r agent/VLN-CE/requirements.txt
pip install setuptools==59.5.0
pip install lmdb==0.98
pip install webdataset==0.1.40
```

## 7. Download Dataset

The `download_mp.py` script for Matterport3D must be obtained via official email after signing the terms of use. 

**Note:** After the `habitat` task data download finishes, press **CTRL-C** to terminate the process. If you continue, the script will proceed to download the entire Matterport3D release, which requires approximately 1.3TB of disk space.

```bash
# 1. Download and extract Matterport3D Dataset 
python3 download_mp.py -o Data/scene_datasets --task habitat
unzip Data/scene_datasets/v1/tasks/mp3d_habitat.zip -d Data/scene_datasets

# 2. Download and extract HA-R2R and HAPS 2.0 datasets
bash scripts/download_data.sh

# 3. Download and extract pre-trained DD-PPO model weights
wget https://dl.fbaipublicfiles.com/habitat/data/baselines/v1/ddppo/ddppo-models.zip
unzip ddppo-models.zip -d Data/ddppo-models/
```

## 8. Human-Scene Fusion

Run the following script to generate multi-view human annotation videos. The output path is configurable in `scripts/human_scene_fusion.py`.

```bash
cd scripts
python3 human_scene_fusion.py
```

## 9. Manual Navigation

Navigate through a scene using the keyboard. Update the `DATA_PATH` in `scripts/demo.py` at line 15 to your local project path before running.

```bash
cd scripts
python demo.py --scan 1LXtFkjw3qL
```

## 10. Real-time Human Rendering

Human rendering is managed by the `HAVLNCE` class in `HASimulator/enviorments.py`. It handles model management and navmesh updates.

The navmesh is computed during the first execution and cached for future use. To enable this feature, update the HAVLN-CE task configuration:

```yaml
SIMULATOR:
  ADD_HUMAN: True
  HUMAN_GLB_PATH: ../Data/HAPS2_0
  HUMAN_INFO_PATH: ../Data/Multi-Human-Annotations/human_motion.json
  RECOMPUTE_NAVMESH_PATH: ../Data/recompute_navmesh
```

## 11. Training, Evaluation and Inference

Execute the following commands to run the HA-VLN-CMA agent:

```bash
cd agent
# Training
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type train

# Evaluation
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type eval

# Inference
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type inference
```
