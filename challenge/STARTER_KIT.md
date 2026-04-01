# HA-VLN Challenge - Starter Kit

## Overview

This starter kit provides templates, utilities, and examples to help you develop and submit solutions to the HA-VLN challenge.

## Quick Start

### 1. Understand the Task

- Read [SUBMISSION_FORMAT.md](SUBMISSION_FORMAT.md) - Required submission format
- Read [EVALUATION_GUIDE.md](EVALUATION_GUIDE.md) - How evaluation works
- Review example submissions in `examples/`

**Key Points**:
- Submit action sequences (0: STOP, 1: MOVE_FORWARD, 2: TURN_LEFT, 3: TURN_RIGHT)
- All 3408 test episodes required
- JSON format with specific schema

### 2. Download Data

```bash
# Check that data is available
ls -lh Data/HA-R2R/test.json.gz
ls -lh Data/HA-R2R/test_gt.json.gz
ls -lh Data/HA-R2R-tools/collision_num_test.json

# If missing, download from challenge website
```

### 3. Develop Your Solution

See `template_solution.py` for a starting point.

### 4. Generate Submission

```bash
python template_solution.py \
  --output submission.json \
  --num_episodes 3408 \
  --seed 42
```

### 5. Validate Submission

```bash
# Quick validation
python -c "
import json
with open('submission.json') as f:
    data = json.load(f)
    print(f\"Episodes: {len(data['episodes'])}\")"
```

### 6. Run Evaluator

```bash
python challenge/evaluator.py submission.json
# Results in ./eval_results/
```

## File Structure

```
challenge/
├── README.md                  # Challenge overview
├── SUBMISSION_FORMAT.md       # Required format spec
├── EVALUATION_GUIDE.md        # How evaluation works
├── evaluator.py              # Main evaluation script
├── config.json               # Evaluator configuration
│
├── examples/
│   ├── random_baseline.json          # Example 1: Random policy
│   ├── forward_walk.json             # Example 2: Simple forward
│   └── il_baseline.json              # Example 3: Learned model
│
└── starter_kit/
    ├── template_solution.py          # Starting template
    ├── utils.py                      # Helper utilities
    ├── requirements.txt              # Dependencies
    └── README.md                     # This file
```

## Templates

### Basic Solution Template

See `template_solution.py`:

```python
import json
from argparse import ArgumentParser

def generate_submission(num_episodes, seed=None):
    """Generate submission with random actions"""
    import random
    if seed is not None:
        random.seed(seed)
    
    episodes = []
    for ep_id in range(num_episodes):
        # Generate actions (example: random policy)
        num_actions = random.randint(1, 50)
        actions = [random.randint(0, 3) for _ in range(num_actions)]
        actions[-1] = 0  # Ensure STOP at end
        
        episodes.append({
            "episode_id": f"{ep_id:06d}",
            "trajectory_id": f"traj_{ep_id}",
            "scene_id": "placeholder",
            "actions": actions
        })
    
    return {
        "metadata": {
            "team_name": "My Team",
            "model": "my_model",
            "description": "My solution"
        },
        "episodes": episodes
    }

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--output", default="submission.json")
    parser.add_argument("--num_episodes", type=int, default=3408)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    
    submission = generate_submission(args.num_episodes, args.seed)
    
    with open(args.output, 'w') as f:
        json.dump(submission, f, indent=2)
    
    print(f"Saved {len(submission['episodes'])} episodes to {args.output}")
```

### Integration with Habitat

If using Habitat for inference:

```python
from habitat import Env
from habitat.core.logging import logger
import json

# Load config
config = habitat.get_config("path/to/config.yaml")
env = Env(config)

episodes = []
for ep_id in range(num_episodes):
    obs = env.reset()
    
    # Your inference logic here
    actions = my_model.predict(obs)
    
    # Ensure proper format
    if actions[-1] != 0:
        actions.append(0)  # Add STOP at end
    
    episodes.append({
        "episode_id": f"{ep_id:06d}",
        "trajectory_id": "...",
        "scene_id": "...",
        "actions": actions
    })

env.close()

# Save
with open("submission.json", 'w') as f:
    json.dump({"episodes": episodes}, f)
```

## Data Details

### Test Split

**File**: `Data/HA-R2R/test.json.gz`

```json
{
  "episodes": [
    {
      "episode_id": "000000",
      "trajectory_id": "traj_0",
      "scene_id": "2n8kARJN3HM",
      "start_position": [12.345, 0.0, 10.234],
      "start_heading": 0.0,
      "instruction_id": "instr_0",
      "instruction": "Go to the kitchen and wait by the refrigerator",
      "reference_path": [[12.345, 0.0, 10.234], ...],
      "info": {...}
    },
    ...
  ],
  "instruction_vocab": {...}
}
```

**Key Fields**:
- `episode_id`: Unique identifier (submit actions for this)
- `scene_id`: Matterport3D scene ID
- `start_position`: Initial position [x, y, z] in meters
- `start_heading`: Initial heading in radians
- `instruction`: Natural language instruction
- `reference_path`: Ground-truth trajectory waypoints

### Ground Truth (test_gt.json.gz)

Available only to evaluator. Contains:
- `goals`: Target positions
- `reference_path`: Full trajectory

## Evaluation Metrics

### Public Leaderboard (Ranked By)

1. **SR_human** (Success Rate, Human-Aware)
   - Primary ranking metric
   - Combination of reaching goal + avoiding excess collisions
   - Range: [0, 1], higher is better

2. **SPL** (Success weighted Path Length)
   - Efficiency metric
   - Rewards both success and short paths
   - Range: [0, 1]

3. **nDTW** (Normalized Dynamic Time Warping)
   - Path alignment to reference
   - Range: [0, 1]

### Detailed Metrics (in results)

- **Success**: Did agent reach goal?
- **Path Length**: Total distance traveled
- **Collisions**: Number of human collisions
- **TCR**: Total Corrective Reward
- **sDTW**: Success-weighted DTW

See EVALUATION_GUIDE.md for detailed descriptions.

## Important Notes

### Action Space

| Action | Code | Semantics                    |
|--------|------|------------------------------|
| STOP   | 0    | End episode, measure success |
| FORWARD| 1    | Move 0.25m in heading direction |
| LEFT   | 2    | Rotate 15° counter-clockwise |
| RIGHT  | 3    | Rotate 15° clockwise |

### Episode Termination

Episodes end when:
1. Agent executes STOP action (code 0), OR
2. Agent takes 500 steps (MAX_STEPS)

**Recommendation**: Always explicitly STOP to avoid wasting steps.

### Trajectory Format (Optional)

You can optionally include predicted trajectory for visualization:

```json
{
  "episode_id": "000000",
  "actions": [1, 1, 1, 0],
  "trajectory": [
    {"position": [0.0, 0.0, 0.0], "heading": 0.0},
    {"position": [0.25, 0.0, 0.0], "heading": 0.0},
    {"position": [0.5, 0.0, 0.0], "heading": 0.0},
    {"position": [0.75, 0.0, 0.0], "heading": 0.0}
  ]
}
```

Useful for debugging and visualization.

## Common Pitfalls

### 1. Incomplete Submissions

**Problem**: Submitting < 3408 episodes

**Solution**: Generate actions for all test episodes
- Use test.json.gz to get all episode_ids
- Ensure no missing episodes

```python
import gzip, json

# Load test split
with gzip.open('Data/HA-R2R/test.json.gz') as f:
    test_data = json.load(f)

test_episode_ids = {str(e['episode_id']) for e in test_data['episodes']}
print(f"Need {len(test_episode_ids)} episodes")

# Check submission
with open('submission.json') as f:
    submission = json.load(f)

submitted_ids = {str(e['episode_id']) for e in submission['episodes']}
missing = test_episode_ids - submitted_ids
print(f"Missing {len(missing)} episodes")
```

### 2. Invalid Action Codes

**Problem**: Using codes outside [0, 1, 2, 3]

**Solution**: Ensure your model outputs valid codes only

```python
# Clamp to valid range
actions = np.clip(predictions, 0, 3).astype(int).tolist()
```

### 3. No STOP Action

**Problem**: Episode doesn't end with STOP, wastes steps

**Solution**: Explicitly add STOP at end

```python
if actions[-1] != 0:
    actions.append(0)  # Add STOP
```

### 4. Wrong Episode IDs

**Problem**: Using mismatched scene_id or trajectory_id

**Solution**: Copy exact values from test.json.gz

```python
import gzip, json, shutil

with gzip.open('Data/HA-R2R/test.json.gz') as f:
    test_data = json.load(f)

episodes = []
for test_episode in test_data['episodes']:
    actions = my_model.predict(test_episode)
    
    episodes.append({
        "episode_id": test_episode["episode_id"],  # Copy exactly
        "trajectory_id": test_episode["trajectory_id"],
        "scene_id": test_episode["scene_id"],
        "actions": actions
    })
```

## Performance Benchmarks

Typical performance ranges (for reference):

| Agent Type       | SR_Human | SPL   | Notes                |
|------------------|----------|-------|----------------------|
| Random walk      | 0.02     | 0.01  | Non-random baseline  |
| Forward walk 50  | 0.12     | 0.08  | Simple baseline      |
| Learned baseline | 0.40     | 0.35  | IL from data         |
| Optimized model  | 0.55     | 0.50  | Good performance     |
| Theoretical max  | 0.85     | 0.70  | With human help      |

## Getting Help

### Documentation

1. [SUBMISSION_FORMAT.md](../SUBMISSION_FORMAT.md) - Format specification
2. [EVALUATION_GUIDE.md](../EVALUATION_GUIDE.md) - Evaluation details
3. Example submissions in `examples/`

### Debugging

1. **Validation errors**: Check against examples/
2. **Low metrics**: Review EVALUATION_GUIDE.md "Interpreting Results"
3. **Missing episodes**: Use the missing episode detection code above
4. **Metric anomalies**: Check per_episode.json for specific failures

### Contact

- **Format questions**: See SUBMISSION_FORMAT.md FAQ
- **Evaluation questions**: See EVALUATION_GUIDE.md
- **High-level questions**: Check challenge website

## Next Steps

1. ✅ Review examples
2. ✅ Understand submission format
3. 🚀 Develop your solution
4. ✅ Validate locally
5. ✅ Submit to leaderboard
6. 📊 Monitor results
7. 🔄 Iterate and improve

Good luck!
