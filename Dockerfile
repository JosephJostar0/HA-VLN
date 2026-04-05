# 1. Base Image: CUDA 11.8 and Ubuntu 22.04 for H100 (sm_90) compatibility
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# 2. Install system dependencies for headless rendering and compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev libglm-dev libgl1 libegl1-mesa-dev mesa-utils \
    xorg-dev freeglut3-dev libcrypt-dev libffi-dev unzip git wget curl ca-certificates \
    ninja-build vim build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Install Miniforge (Mamba) for faster dependency resolution
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniforge.sh && \
    /bin/bash ~/miniforge.sh -b -p /opt/conda && \
    rm ~/miniforge.sh
ENV PATH=$CONDA_DIR/bin:$PATH

# 4. Create Conda environment with GCC 11 toolchain (to avoid libstdc++ conflicts)
RUN mamba create -n havlnce python=3.8 \
    gcc_linux-64=11 gxx_linux-64=11 sysroot_linux-64=2.17 \
    -c conda-forge -y

# Set the shell to use the conda environment for subsequent RUN commands
SHELL ["conda", "run", "-n", "havlnce", "/bin/bash", "-c"]

# 5. Install H100 compatible PyTorch 2.0.1
RUN pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 \
    --index-url https://download.pytorch.org/whl/cu118

# 6. Install Habitat-Sim (Headless version via Mamba)
RUN mamba install -y -c aihabitat -c conda-forge "habitat-sim=0.1.7=*headless*"

# 7. Setup the working directory and clone the official HA-VLN repository
WORKDIR /app
# Note: Currently using the full official repo. Later, this will point to the Challenge Repo without agent/Data.
RUN git clone https://github.com/F1y1113/HA-VLN.git .

# 8. Setup Habitat-Lab (v0.1.7)
RUN git clone --branch v0.1.7 https://github.com/facebookresearch/habitat-lab.git /app/habitat-lab
WORKDIR /app/habitat-lab
# Apply patch 1: Fix Discrete(0) for modern Gym compatibility
RUN sed -i 's/spaces.Discrete(0)/spaces.Discrete(4)/g' habitat/tasks/vln/vln.py
# Apply patch 2: Downgrade setuptools to avoid use_2to3 build errors in legacy code
RUN pip install --upgrade pip wheel Cython && \
    pip install setuptools==59.5.0 msgpack "numpy<1.24.0" tensorboard && \
    sed -i 's/tensorflow==1.13.1/# tensorflow==1.13.1/g' habitat_baselines/rl/requirements.txt && \
    pip install -r requirements.txt && \
    pip install -r habitat_baselines/rl/requirements.txt && \
    pip install -e .

# 9. Setup GroundingDINO (Required by HASimulator)
WORKDIR /app/HASimulator
RUN git clone https://github.com/IDEA-Research/GroundingDINO.git
WORKDIR /app/HASimulator/GroundingDINO
# Clean build cache and install
RUN rm -rf build/ dist/ *.egg-info && \
    pip install "safetensors==0.3.1" "huggingface-hub==0.16.4" "tokenizers==0.13.3" "transformers==4.30.2" "timm==0.9.2" && \
    sed -i 's/supervision.*/supervision==0.11.1/g' requirements.txt && \
    pip install ninja && \
    pip install -e . && \
    mkdir weights && cd weights && \
    wget -q --no-check-certificate https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth

# 10. Install HA-VLN Simulator dependencies
WORKDIR /app
RUN pip install "Pillow<9.0.0" webdataset==0.1.40
RUN cd HASimulator && pip install -e .

# 11. Final environment configuration
# Ensure the user's agent directory and Data directory exist as mount points
RUN mkdir -p /app/agent /app/Data /app/result

# Set Environment Variables for Headless EGL rendering and library linking
ENV CUDA_HOME=/usr/local/cuda
ENV EGL_DEVICE_ID=0
ENV CUDA_VISIBLE_DEVICES=0
ENV DISPLAY=""
ENV LD_LIBRARY_PATH=$CONDA_DIR/envs/havlnce/lib:$CUDA_HOME/lib:$LD_LIBRARY_PATH

# 12. Security: Lock official directories to Read-Only (except for Data/Agent/result which are mounted)
# This prevents participants from modifying the simulator or library code at runtime.
RUN chmod -R 555 /app/habitat-lab /app/HASimulator

# Default entry point
WORKDIR /app
RUN echo "source activate havlnce" >> ~/.bashrc
CMD ["/bin/bash"]