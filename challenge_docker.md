# 🏆 HA-VLN Challenge 2026: Local Evaluation Guide

Welcome to the HA-VLN Challenge! To ensure fairness and reproducibility, all submissions will be evaluated inside an isolated, standardized Docker container on an NVIDIA H100 (sm_90) cluster.

This guide will help you set up the official Docker environment locally so you can test your agent before submitting it to EvalAI.

## 🧱 The Evaluation Environment

The official evaluation image (`havln-eval-image:v1`) contains:
- **OS & Hardware drivers**: Ubuntu 22.04, CUDA 11.8, and required EGL headless rendering libraries.
- **Python Environment**: A pre-configured Conda environment (`havlnce`) with Python 3.8 and PyTorch 2.0.1.
- **Locked Official Code**: Pre-installed and patched `habitat-lab`, `habitat-sim`, and the official `HASimulator`. **These directories are Read-Only (chmod 555) to prevent runtime modifications.**

## 📦 How Submissions Work (Bring Your Own Agent)

We allow participants to use **any agent architecture**. You do not need to strictly follow our baseline. 

You only need to submit a `submission.zip` file containing your agent code, model weights, and a starting script named `run.sh`. 

### Submission Directory Structure
Your `submission.zip` must unzip to the following structure:
```text
submission/
├── run.sh             # The main executable script (Must be named run.sh)
├── requirements.txt   # (Optional) If your agent needs extra pip packages
├── your_agent.py      # Your custom policy/agent logic
├── weights/           # Your pre-trained model weights
└── ...                # Any other necessary scripts
```

## 🧪 Testing Your Agent Locally (Highly Recommended)

We use a **Modular Mounting Strategy**. During evaluation, the container will mount your code, the hidden test data, and the output directory into specific locations.

### Step 1: Pull/Build the Evaluation Image
*(Assuming the image is uploaded to DockerHub)*
```bash
docker pull your_org/havln-eval-image:v1
```

### Step 2: Run the Local Evaluation
To simulate the exact evaluation process, run the following Docker command. Make sure to replace the `/path/to/...` with your actual local absolute paths.

```bash
docker run --rm -it \
    --gpus all \
    --runtime=nvidia \
    -v /path/to/your/local/Data:/app/Data:ro \
    -v /path/to/your/submission:/app/agent:ro \
    -v /path/to/your/output_dir:/app/result:rw \
    your_org/havln-eval-image:v1 \
    bash /app/agent/run.sh
```

### Important Notes on Paths:
1. **Data (`/app/Data:ro`)**: Your code should always read datasets from `../Data/` or `/app/Data/`. It is mounted as **Read-Only**.
2. **Agent (`/app/agent:ro`)**: Your submission is mounted as **Read-Only**. Your code cannot write files to its own directory during runtime.
3. **Result (`/app/result:rw`)**: The official `HASimulator` evaluator will automatically generate `result.json` here. If your agent needs to save logs, write them to `/app/result/`.

## ⚙️ Example `run.sh`

Your `run.sh` will be executed directly by the evaluator. Here is a baseline example:

```bash
#!/bin/bash

# 1. Activate the official environment
source activate havlnce

# 2. (Optional) Install your specific agent dependencies
# pip install -r /app/agent/requirements.txt

# 3. Run your agent inference
# Note: The official simulator will automatically intercept the 'done' signal 
# and write the final metrics to /app/result/result.json
python /app/agent/your_agent.py --cfg /app/agent/configs/test.yaml
```
