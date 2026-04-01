# HA-VLN Agent Integration Technical Documentation

This document explains how to integrate a static Vision-and-Language Navigation (VLN) Agent based on the Habitat framework into the HA-VLN dynamic environment. The integration process consists of four independent configuration and development levels: Configuration Level, Environment Interface Level, Dataset and Vocabulary Level, and Evaluation Metrics Level.

## 1. Configuration Level

When integrating into the HA-VLN environment, it is necessary to redirect the Agent's original task configuration file and modify parameters to support the rendering and evaluation of dynamic human models.

### 1.1 Task Configuration Redirection
Point the base task configuration file path in the Agent's configuration to the HA-VLN environment configuration.
```yaml
# Example: Before modification
# BASE_TASK_CONFIG_PATH: habitat_extensions/config/vlnce_task.yaml

# After modification: Point to HA-VLN configuration
BASE_TASK_CONFIG_PATH: path/to/HASimulator/config/HAVLNCE_task.yaml
```

### 1.2 Path Configuration Instructions
`HAVLNCE_task.yaml` contains multiple relative path definitions (e.g., `../Data/`). These paths are relative to the Current Working Directory (CWD) of the HA-VLN startup script. If the Agent runs in a different directory, these must be modified to absolute paths to prevent file reading errors.

### 1.3 Core Environment Parameters
In `HAVLNCE_task.yaml`, ensure the following parameters meet the dynamic environment requirements:
* `ADD_HUMAN: True`: Enables the loading and rendering of 3D dynamic human models.
* `ALLOW_SLIDING: True`: Recommended to enable. Prevents the Agent from getting stuck due to physical collisions with dynamic obstacles.
* `HUMAN_COUNTING: True`: (Optional) Enable this if using a vision model to count the number of people in the field of view. **Note**: Before enabling this feature, ensure GroundingDINO is correctly installed and its absolute path is configured in `detector.py`.

### 1.4 Evaluation Metrics Configuration
To support subsequent dynamic obstacle avoidance evaluation, the `TASK.MEASUREMENTS` list must include the following specific metrics:
```yaml
  MEASUREMENTS: [
    # ... other base metrics
    COLLISIONS_DETAIL,  # Records the specific objects involved in collisions
    DISTANCE_TO_HUMAN   # Records the distance and angle relative to human models
  ]
```

### 1.5 Experimental Baseline Switching
The system provides four preset configuration files. Switch them by modifying `BASE_TASK_CONFIG_PATH` to support ablation studies:
1.  `HAVLNCE_task.yaml`: Dynamic environment + HA-R2R complex instructions.
2.  `HAVLNCE_R2R_task.yaml`: Dynamic environment + original R2R instructions.
3.  `VLNCE_task.yaml`: Static environment + original R2R instructions.
4.  `VLNCE_HAR2R_task.yaml`: Static environment + HA-R2R complex instructions.

---

## 2. Environment Interface Level

HA-VLN uses an independent child thread to maintain physical time progression (set to send a rendering signal every 0.1 seconds). To synchronize the Agent's stepping with the physics engine's state, signal interception and processing must be implemented in the Environment Wrapper.

### 2.1 Wrapper Class Implementation
Create or modify the Agent's environment wrapper class. Before calling the parent class's `step` method, process the clock signal queue to ensure the underlying NavMesh and human models are updated.

```python
from habitat.core.env import Env
from HASimulator.environments import HAVLNCE

class HAVLNWrapper(Env):
    """HA-VLN Dynamic Environment Synchronization Wrapper Class"""
    
    def __init__(self, config, dataset=None):
        super().__init__(config, dataset)
        self.use_dynamic_human = getattr(self._config.TASK_CONFIG.SIMULATOR, "ADD_HUMAN", False)
        
        if self.use_dynamic_human:
            self.havlnce_tool = HAVLNCE(self._config.TASK_CONFIG, self._sim)
            self.havlnce_tool._reset_signal_queue_and_counters()
        
    def reset(self):
        if self.use_dynamic_human:
            self.havlnce_tool.reset()
        observations = super().reset()
        return observations
        
    def step(self, action):
        if self.use_dynamic_human:
            # Synchronize the physical timeline, process rendering signals, and recompute NavMesh
            self.havlnce_tool._handle_signals()
        
        observations, reward, done, info = super().step(action)
        return observations, reward, done, info
```

---

## 3. Dataset and Vocabulary Level

The HA-R2R dataset contains newly added vocabulary describing human behaviors. If the Agent uses a fixed vocabulary maintained in a static file (e.g., `.txt`), an expansion operation is required to avoid Out-Of-Vocabulary (OOV) errors. (Note: Agents using pre-trained models with built-in Tokenizers can skip this step).

### 3.1 Vocabulary Expansion Script
The following script extracts new vocabulary from the HA-R2R dataset and appends it to the end of the existing vocabulary file.

```python
import json
import gzip
import re
from pathlib import Path

def clean_text(text: str) -> list:
    """Clean instruction text and tokenize"""
    text = text.lower()
    text = re.sub(r'([.?!,;:/\\()\[\]"\'\-])', r' \1 ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.split()

def update_vocabulary(ha_r2r_dir: str, existing_vocab_path: str, output_vocab_path: str):
    """Extract new vocabulary and generate an updated vocabulary file"""
    ha_r2r_path = Path(ha_r2r_dir)
    
    with open(existing_vocab_path, 'r', encoding='utf-8') as f:
        existing_words = [line.strip() for line in f.readlines()]
    
    vocab_set = set(existing_words)
    new_words = []

    for split in ['train', 'val_seen', 'val_unseen']:
        json_file = ha_r2r_path / split / f"{split}.json.gz"
        if not json_file.exists():
            continue
            
        with gzip.open(json_file, 'rt', encoding='utf-8') as f:
            data = json.load(f)
            
        for item in data:
            for instruction in item.get('instructions', []):
                tokens = clean_text(instruction)
                for token in tokens:
                    if token not in vocab_set:
                        vocab_set.add(token)
                        new_words.append(token)

    with open(output_vocab_path, 'w', encoding='utf-8') as f:
        for word in existing_words + new_words:
            f.write(f"{word}\n")

if __name__ == "__main__":
    HA_R2R_DATA_DIR = "../Data/HA-R2R"
    OLD_VOCAB = "../HASimulator/HA-DE/tasks/HA/data/train_vocab.txt"
    NEW_VOCAB = "../Data/ha_r2r_vocab.txt"
    update_vocabulary(HA_R2R_DATA_DIR, OLD_VOCAB, NEW_VOCAB)
```

---

## 4. Evaluation Metrics Level

HA-VLN introduces the Trajectory Collision Rate (TCR) and a strictly constrained Success Rate (SR). Because a tracking dictionary containing high-dimensional data is introduced, it must be intercepted, calculated, and stripped from the main metrics dictionary during the evaluation process to prevent errors in subsequent averaging operations.

### 4.1 Metrics Calculation Logic
* **TCR Calculation**: Current total collisions minus the basic environmental collisions recorded by the Oracle optimal path. A result greater than 0 indicates an extra collision with a dynamic obstacle (human body).
* **SR Calculation**: Based on the original success state, a strong constraint of `TCR == 0` is added.

### 4.2 Evaluation Loop Integration Example
Integrate the `Calculate_Metric` class into the Agent's evaluation loop and process non-scalar data.

```python
from HASimulator.metric import Calculate_Metric

# 1. Instantiate the calculation class, passing the current data split (e.g., 'val_unseen')
ha_metric_calculator = Calculate_Metric(split="val_unseen")
stats_info = {}

# 2. Integrate calculation and data stripping in the Episode completion logic
# Assuming ep_id is the current Episode ID, and infos[i] is the info dictionary returned by the environment
ep_id = current_episodes[i].episode_id
stats_episodes[ep_id] = infos[i]

# Calculate TCR, CR, and strict SR
ha_metric_calculator(stats_episodes[ep_id], ep_id)

# 3. Strip high-dimensional non-scalar data
keys = list(stats_episodes[ep_id].keys())
if 'distance_to_human' in keys or 'collisions_detail' in keys:
    if str(ep_id) not in stats_info:
        stats_info[ep_id] = {}
        
    if 'distance_to_human' in keys:
        stats_info[ep_id]['distance_to_human'] = stats_episodes[ep_id].pop('distance_to_human')
    if 'collisions_detail' in keys:
        stats_info[ep_id]['collisions_detail'] = stats_episodes[ep_id].pop('collisions_detail')
```

## 5. Visualization and Debugging Level

In the HA-VLN dynamic environment, visualization is a critical step for verifying the Agent's obstacle avoidance strategies and human awareness capabilities. By collecting observation images during the evaluation phase, appending instruction text, and optionally integrating the output of object detection models, a complete video record of the Agent's navigation process can be synthesized.

### 5.1 Dependency Modules
The visualization pipeline primarily relies on the following utility functions:
* `observations_to_image`: Concatenates the Agent's multi-modal observations (e.g., RGB, depth map, top-down map) into a single image frame.
* `append_text_to_image`: Overlays the current natural language navigation instruction at the top of the image frame.
* `generate_video`: Encodes the collected sequence of image frames and saves it as a local video file (e.g., MP4).

### 5.2 Observation and Object Detection Fusion (Optional)
If `HUMAN_COUNTING` is enabled in the configuration file, the system will call the GroundingDINO detector to identify human models within the field of view. The rendered image with bounding boxes must replace the original RGB observation before frame concatenation.

### 5.3 Evaluation Loop Integration Code
Within the Agent's evaluation stepping loop (typically located in the `_eval_checkpoint` method), implement the following logic to collect image frames and generate videos:

```python
from copy import deepcopy
from habitat_extensions.utils import observations_to_image, generate_video
from habitat.utils.visualizations.utils import append_text_to_image

# Initialize a list to store video frames
# envs.num_envs represents the number of parallel environments
rgb_frames = [[] for _ in range(envs.num_envs)]

# Assuming this is inside the evaluation stepping loop: outputs = envs.step(actions)
# observations, _, dones, infos = [list(x) for x in zip(*outputs)]

for i in range(envs.num_envs):
    # Check if the configuration allows video generation
    if len(config.VIDEO_OPTION) > 0:
        
        # 1. Image processing and observation replacement
        if config.TASK_CONFIG.SIMULATOR.HUMAN_COUNTING:
            # Deep copy to avoid modifying underlying environment data
            observations_ = deepcopy(observations)
            for k in range(len(observations)):
                # detected_img is the image with bounding boxes returned by the prior detector() call
                observations_[k]['rgb'] = detected_img[k]
            frame = observations_to_image(observations_[i], infos[i])
        else:
            # Default concatenation
            frame = observations_to_image(observations[i], infos[i])
        
        # 2. Append text instructions to the current frame
        frame = append_text_to_image(
            frame, current_episodes[i].instruction.instruction_text
        )
        rgb_frames[i].append(frame)

    # 3. Trigger video generation when the Episode ends
    if dones[i]:
        ep_id = current_episodes[i].episode_id
        
        if len(config.VIDEO_OPTION) > 0:
            generate_video(
                video_option=config.VIDEO_OPTION,
                video_dir=config.VIDEO_DIR,
                images=rgb_frames[i],
                episode_id=ep_id,
                checkpoint_idx=checkpoint_index,
                # Record core metrics; can be replaced with TCR / strict_success
                metrics={"spl": stats_episodes[ep_id]["spl"]}, 
                tb_writer=writer,
            )
            # Clear the generated frames list to prepare for the next Episode
            rgb_frames[i] = []
```
