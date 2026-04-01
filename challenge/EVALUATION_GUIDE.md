# HA-VLN Challenge Evaluation Guide

## Overview

This guide explains how the automatic evaluation system works, how to run it, and how to interpret results.

## Evaluation Pipeline

The evaluator implements a **5-stage pipeline**:

```
Stage 1: Submission Validator
    ↓
Stage 2: Action Replayer (Simulator Forward Pass)
    ↓
Stage 3: Metric Engine (Compute all metrics)
    ↓
Stage 4: Aggregator (Mean, std, min, max across episodes)
    ↓
Stage 5: Reporter (Generate leaderboard & detailed results)
```

## Stage Details

### Stage 1: Submission Validator

**Purpose**: Ensure submission format is correct before expensive evaluation.

**Checks**:
- JSON structure validity
- Required fields present: `episode_id`, `trajectory_id`, `scene_id`, `actions`
- Action codes in valid range [0, 1, 2, 3]
- Trajectory length within bounds [1, 500]
- No duplicate episode_ids
- All submitted episodes are in official test split

**Output**: Pass/Fail with detailed error messages

**Example Error**:
```
[ERROR] Episode 000000: Missing field 'actions'
[ERROR] Episode 000001, step 5: invalid action code 7
[WARNING] Missing 123 episodes from test set
```

### Stage 2: Action Replayer

**Purpose**: Convert submitted actions back into 3D trajectories through simulation.

**Process**:
1. Load GT data from `test_gt.json.gz` (contains start positions, goals, reference paths)
2. For each submitted action sequence:
   - Initialize agent at start position with heading=0
   - Execute action 0-3 (STOP, MOVE_FORWARD, TURN_LEFT, TURN_RIGHT)
   - Record position after each step
   - Stop on STOP action or MAX_STEPS

**Action Semantics**:
- **Action 0 (STOP)**: Terminate episode, measure success
- **Action 1 (MOVE_FORWARD)**: Move 0.25m in current heading direction
- **Action 2 (TURN_LEFT)**: Rotate 15° counter-clockwise
- **Action 3 (TURN_RIGHT)**: Rotate 15° clockwise

**Output**: Simulated trajectory (sequence of 3D positions)

### Stage 3: Metric Engine

**Purpose**: Compute all navigation metrics from trajectory.

#### A-Group Metrics (Classic VLN)

**Success (SR)** - Binary success indicator
```
SR = 1 if distance_to_goal ≤ 3.0m else 0
```

**Success Rate Length (SPL)** - Efficiency metric
```
SPL = SR × (reference_path_length / max(reference_path_length, agent_path_length))
```
- Rewards both reaching goal AND taking efficient path
- SPL ∈ [0, 1]

**Normalized DTW (nDTW)** - Path alignment metric
```
dtw_distance = Dynamic Time Warping distance between agent path and GT reference
nDTW = exp(-dtw_distance / (|reference_path| × success_distance))
```
- Measures how closely agent follows reference path
- nDTW ∈ [0, 1], higher = better alignment

**Success-weighted DTW (sDTW)**
```
sDTW = SR × nDTW
```
- Only rewards path alignment if goal reached
- sDTW ∈ [0, 1]

#### B-Group Metrics (Human-Aware)

**Collisions** - Raw collision count
```
collisions = total_collisions_with_humans
```

**Total Corrective Reward (TCR)** - Excess collisions
```
baseline_collisions = historical_human_collision_count[episode_id]
TCR = max(0, agent_collisions - baseline_collisions)
```
- Accounts for episodes naturally having more collisions
- TCR ≥ 0

**Collision Rate (CR)** - Binary collision penalty
```
CR = min(TCR, 1)
```
- CR ∈ [0, 1]: 0 = within baseline, 1 = exceeded

**Success Rate (Human-Aware)** - Success without excess collisions
```
SR_human = SR × I(TCR == 0)
```
- SR_human ∈ [0, 1]: Only 1 if both reach goal AND no excess collisions

#### Oracle Metrics (Reference)

For comparison, evaluator also computes oracle metrics:
- **Oracle Success**: Best reachable goal distance across all trajectory points
- **Oracle SPL**: SPL using oracle success

These help assess path quality vs. goal proximity.

### Stage 4: Aggregator

**Purpose**: Compute summary statistics across all episodes.

For each metric, computes:
```json
{
  "mean": average value,
  "std": standard deviation,
  "min": minimum value,
  "max": maximum value,
  "count": number of valid episodes
}
```

### Stage 5: Reporter

**Purpose**: Generate human-readable leaderboard and detailed results.

**Output Files**:

1. **leaderboard.json** - Public metrics
   ```json
   {
     "sr_human": 0.523,
     "spl": 0.412,
     "ndtw": 0.681,
     "sdtw": 0.357,
     "collisions": 2.14,
     "tcr": 0.89
   }
   ```

2. **per_episode.json** - Detailed results per episode
   ```json
   [
     {
       "episode_id": "000000",
       "success": 1.0,
       "spl": 0.85,
       "path_length": 12.5,
       "ndtw": 0.91,
       "sdtw": 0.91,
       "collisions": 1,
       "tcr": 0,
       "cr": 0.0,
       "sr_human": 1.0,
       "distance_to_goal": 0.5,
       "steps": 50
     },
     ...
   ]
   ```

3. **aggregated.json** - Full statistics
   ```json
   {
     "sr_human": {
       "mean": 0.523,
       "std": 0.499,
       "min": 0.0,
       "max": 1.0,
       "count": 3408
     },
     ...
   }
   ```

4. **summary.txt** - Human-readable report
   ```
   === HA-VLN Challenge Evaluation Summary ===
   
   Timestamp: 2024-01-15T10:30:45.123456
   Episodes evaluated: 3408
   
   Public Leaderboard Metrics:
     sr_human:            0.523077
     spl:                 0.412456
     ndtw:                0.681234
     ...
   ```

## Running the Evaluator

### Prerequisites

```bash
# Install dependencies
pip install numpy
pip install fastdtw  # Optional but recommended for nDTW

# Ensure GT data is available
ls -lh Data/HA-R2R/test_gt.json.gz
ls -lh Data/HA-R2R-tools/collision_num_test.json
```

### Basic Usage

```bash
python challenge/evaluator.py <submission_file>
```

Example:
```bash
python challenge/evaluator.py my_submission.json
```

### Advanced Options

```bash
python challenge/evaluator.py my_submission.json \
  --config challenge/config.json \
  --output ./my_eval_results
```

**Arguments**:
- `submission`: Path to submission JSON file
- `--config`: Path to evaluator configuration (default: `challenge/config.json`)
- `--output`: Output directory for results (default: `./eval_results`)

### Output

Results are saved to the output directory:
```
eval_results/
├── leaderboard.json      # Public leaderboard metrics
├── per_episode.json      # Detailed per-episode results
├── aggregated.json       # Full statistics
└── summary.txt           # Human-readable summary
```

## Interpreting Results

### Leaderboard Ranking

The **primary metric** is `sr_human`:
1. **Sort by sr_human** (descending) - Success with human awareness
2. **Tie-break by spl** (descending) - Efficiency
3. **Tie-break by ndtw** (descending) - Path alignment

### Example Leaderboard

| Rank | Team             | SR_Human | SPL    | nDTW   | sDTW   |
|------|------------------|----------|--------|--------|--------|
| 1    | Team-A           | 0.625    | 0.523  | 0.712  | 0.445  |
| 2    | Team-B           | 0.612    | 0.501  | 0.705  | 0.431  |
| 3    | Team-C           | 0.598    | 0.488  | 0.687  | 0.411  |

### Understanding Your Metrics

**Good Performance**:
- `sr_human > 0.6`: Reaching goals while avoiding humans
- `spl > 0.45`: Efficient paths
- `ndtw > 0.7`: Good path alignment

**Needs Improvement**:
- `sr_human < 0.4`: Failing to reach goals or hitting humans too much
- `spl < 0.3`: Taking very inefficient paths
- `collisions > 3`: Frequently colliding with humans

### Analyzing Per-Episode Failures

Use `per_episode.json` to debug:

```python
import json

with open("per_episode.json") as f:
    results = json.load(f)

# Find episodes where agent failed
failed = [r for r in results if r["success"] == 0.0]
print(f"Failed {len(failed)}/3408 episodes")

# Find high-collision episodes
collisions = [r for r in results if r["collisions"] > 5]
print(f"High-collision episodes: {len(collisions)}")

# Analyze distances
distances = [r["distance_to_goal"] for r in results]
print(f"Avg distance to goal: {sum(distances)/len(distances):.2f}m")
```

## Common Issues

### 1. Submission Validation Failures

**Error**: `Missing field 'episode_id'`
- **Cause**: JSON structure incorrect
- **Fix**: Ensure submission follows SUBMISSION_FORMAT.md exactly

**Error**: `Episode not found in test split`
- **Cause**: Using wrong episode_id
- **Fix**: Verify episode_ids are from official test.json.gz

**Error**: `invalid action code 7`
- **Cause**: Action codes must be 0-3
- **Fix**: Check action generation code, ensure correct values

### 2. High Error Rates

**Error**: `Episode not found in GT`
- **Cause**: Mismatch between test.json.gz and test_gt.json.gz
- **Fix**: Use official data files only; don't modify

### 3. Unexpected Metric Values

**All metrics = 0**: Agent never reaches any goals
- **Check**: Is initial heading calculation correct?
- **Check**: Is forward movement in correct direction?

**SPL very low but Success high**: Paths are very inefficient
- **Check**: Is agent taking unnecessary detours?
- **Check**: Action execution order correct?

## Advanced Topics

### Custom Metric Computation

To verify metrics locally, use per_episode.json:

```python
import json

with open("per_episode.json") as f:
    episodes = json.load(f)

# Compute custom success rate
success_rate = sum(1 for e in episodes if e["success"] == 1.0) / len(episodes)
print(f"Success rate: {success_rate:.4f}")

# Weighted average (if some episodes are harder)
weighted_sr = sum(e.get("sr_human", 0) for e in episodes) / len(episodes)
print(f"Success rate (human-aware): {weighted_sr:.4f}")
```

### Comparing Model Versions

Keep results from different submissions:
```bash
python challenge/evaluator.py v1_submission.json --output results_v1/
python challenge/evaluator.py v2_submission.json --output results_v2/

# Compare leaderboards
python scripts/compare_results.py results_v1/leaderboard.json results_v2/leaderboard.json
```

## Troubleshooting

### Evaluator Crashes

**Error**: `FileNotFoundError: test_gt.json.gz`
- **Fix**: Check config.json paths are correct relative to script location
- **Fix**: Run from workspace root: `cd /home/jojo/gitlib/HA-VLN && python challenge/evaluator.py ...`

**Error**: `fastdtw not found`
- **Fix**: Install optional dependency: `pip install fastdtw`
- **Note**: Will fall back to simple DTW if not installed (slower)

**Error**: `Memory error on large submission`
- **Cause**: Loading entire GT into memory
- **Fix**: Increase available RAM or process in batches

### Validation Issues

**Warning**: `Missing N episodes from test set`
- This is expected if submission only covers subset
- But leaderboard will only rank completeness similarly

**Error**: `Duplicate episode_id`
- **Cause**: Same episode submitted twice
- **Fix**: Remove duplicates from submission

### Metric Anomalies

**Question**: Why is my sDTW higher than nDTW?
- **Answer**: sDTW = Success × nDTW, so sDTW ≤ nDTW always
- If sDTW > nDTW, there's a bug - report to organizers

**Question**: Why is SR_human sometimes < Success?
- **Answer**: SR_human = Success × (TCR == 0), so SR_human ≤ Success
- If SR_human > Success, there's a bug - report to organizers

## Performance Benchmarks

For reference, here are typical metric ranges:

| Agent Type          | SR_Human | SPL   | nDTW  | Notes                            |
|---------------------|----------|-------|-------|----------------------------------|
| Random actions      | ~0.05    | ~0.02 | ~0.15 | Baseline for validation          |
| Shortest path       | ~0.45    | ~0.80 | ~0.85 | Oracle reference                 |
| Learned baseline    | ~0.40    | ~0.35 | ~0.60 | From related work                |
| Human performance   | ~0.85    | ~0.70 | ~0.90 | Upper bound                      |
| Optimized agent     | ~0.55    | ~0.50 | ~0.75 | Realistic top performance        |

## Support

For evaluation-related issues:
1. Check this guide for similar issues
2. Review SUBMISSION_FORMAT.md for format details
3. See per_episode.json for specific failing episodes
4. Contact organizers with: submission file, error message, and config.json

## Appendix: Configuration Reference

See `config.json`:

```json
{
  "paths": {
    "test_path": "Data/HA-R2R/test.json.gz",
    "test_gt_path": "Data/HA-R2R/test_gt.json.gz",
    "collision_stats_path": "Data/HA-R2R-tools/collision_num_{split}.json"
  },
  "parameters": {
    "success_distance": 3.0,
    "forward_step_size": 0.25,
    "turn_angle": 15,
    "max_steps": 500
  }
}
```

### Parameter Meanings

- **success_distance**: Goal reached if distance < 3.0m (standard in VLN)
- **forward_step_size**: 0.25m per MOVE_FORWARD action (small steps for precision)
- **turn_angle**: 15° per turn action
- **max_steps**: 500 step limit per episode (prevents infinite loops)

All parameters are fixed for the challenge and cannot be changed by participants.
