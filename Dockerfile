# 1. 基础镜像：H100 兼容的 CUDA 11.8 和 Ubuntu 22.04 (系统原生自带 GCC 11)
FROM nvidia/cuda:11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# 2. 安装系统依赖 (补充 libffi-dev，把底层依赖交给最稳定的 Ubuntu APT 管理)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev libglm-dev libgl1 libegl1-mesa-dev mesa-utils \
    xorg-dev freeglut3-dev libcrypt-dev libffi-dev unzip git wget curl ca-certificates ninja-build vim \
    && rm -rf /var/lib/apt/lists/*

# 3. 安装 Miniforge (无条款限制，自带极速 mamba 解算器)
ENV CONDA_DIR=/opt/conda
RUN wget --quiet https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniforge.sh && \
    /bin/bash ~/miniforge.sh -b -p /opt/conda && \
    rm ~/miniforge.sh
ENV PATH=$CONDA_DIR/bin:$PATH

# 4. 创建纯净的 Conda 环境 (砍掉 Conda GCC，完美避开底层库冲突)
RUN mamba create -n havlnce python=3.8 -c conda-forge -y

# 切换默认 shell 以便在构建时自动激活 conda 环境
SHELL ["conda", "run", "-n", "havlnce", "/bin/bash", "-c"]

# 5. 安装 PyTorch (H100 专属)
ENV CUDA_HOME=/usr/local/cuda
RUN pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 --index-url https://download.pytorch.org/whl/cu118

# 6. 安装 Habitat-Sim 和 Habitat-Lab (纯净安装，秒级解算)
# 6. 安装 Habitat-Sim (单独一步，确保 Mamba 环境纯净)
WORKDIR /workspace
RUN mamba install -y -c aihabitat -c conda-forge "habitat-sim=0.1.7=*headless*"

# 7. 克隆 Habitat-Lab 源码
RUN git clone --branch v0.1.7 https://github.com/facebookresearch/habitat-lab.git

# 8. 切换到源码目录 (使用 Docker 的 WORKDIR 代替 cd，极其关键)
WORKDIR /workspace/habitat-lab

# 9. 安装 Python 基础编译工具和前置依赖 (必须严格锁定 setuptools==59.5.0)
RUN pip install --upgrade pip wheel Cython && \
    pip install setuptools==59.5.0 msgpack "numpy<1.24.0" tensorboard lmdb

# 10. 修改不兼容的旧版配置
RUN sed -i 's/tensorflow==1.13.1/# tensorflow==1.13.1/g' habitat_baselines/rl/requirements.txt && \
    sed -i 's/spaces.Discrete(0)/spaces.Discrete(4)/g' habitat/tasks/vln/vln.py

# 11. 依次安装 requirements 并执行 setup.py 编译
RUN pip install -r requirements.txt
RUN pip install -r habitat_baselines/rl/requirements.txt
RUN pip install -e .

# 接下来的步骤还是你原来的 编译 GroundingDINO 等等...
# (记得把下面的步骤编号顺延一下)

# 7. 编译 GroundingDINO (原生系统编译，告别 types.h 补丁)
RUN git clone https://github.com/IDEA-Research/GroundingDINO.git && \
    cd GroundingDINO && \
    pip install "safetensors==0.3.1" "huggingface-hub==0.16.4" "tokenizers==0.13.3" "transformers==4.30.2" "timm==0.9.2" && \
    sed -i 's/supervision.*/supervision==0.11.1/g' requirements.txt && \
    pip install ninja && \
    pip install -e . && \
    mkdir weights && cd weights && \
    wget -q --no-check-certificate https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth

# 8. 安装基础通用库
RUN pip install "Pillow<9.0.0" setuptools webdataset==0.1.40

# 9. 环境变量配置
WORKDIR /app
ENV EGL_DEVICE_ID=0
ENV CUDA_VISIBLE_DEVICES=0
ENV DISPLAY=""
ENV LD_LIBRARY_PATH=$CUDA_HOME/lib:$LD_LIBRARY_PATH

RUN echo "source activate havlnce" >> ~/.bashrc
CMD ["/bin/bash"]