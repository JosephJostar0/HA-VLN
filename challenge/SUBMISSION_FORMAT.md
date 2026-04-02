# HA-VLN Challenge - Submission Format Specification

## Overview

Participants must submit **action sequence** files. The organizers will privately replay these actions in the HA-VLN simulator to compute all evaluation metrics.

## Submission Schema

### File Format
- **Format**: JSON
- **Units**:
  - position: meters (m)
  - heading: radians (rad)
  - action codes: integers

### JSON Structure

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [0, 2, 2, 1, 1, 3],
      "trajectory": [
        {
          "position": [6.307, 0.121, 0.185],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.407],
          "heading": -0.259,
          "stop": false
        }
      ]
    }
  ],
  "metadata": {
    "agent_name": "MyAgent",
    "timestamp": "2026-03-31T12:00:00Z",
    "split": "test"
  }
}
```

### Field Descriptions

#### Required Fields

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `episode_id` | string | Required | Unique episode identifier, must match `episode_id` in `test.json.gz` |
| `trajectory_id` | string | Required | Unique trajectory identifier, must match `trajectory_id` in `test.json.gz` |
| `scene_id` | string | Required | Scene ID, must match `scene_id` in `test.json.gz` |
| `actions` | array[int] | Required | Action sequence, length > 0 and ≤ 500 |

#### Action Codes

| Code | Action Name | Description |
|------|-------------|-------------|
| 0 | STOP | Stop navigation, end episode |
| 1 | MOVE_FORWARD | Move forward 0.25m |
| 2 | TURN_LEFT | Turn left 15° |
| 3 | TURN_RIGHT | Turn right 15° |

#### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `trajectory` | array[dict] | Observation states for each step (for auditing and visualization only, not used for scoring) |
| `trajectory[i].position` | array[float] | XYZ coordinates after step i |
| `trajectory[i].heading` | float | Heading after step i (radians, range [-π, π]) |
| `trajectory[i].stop` | bool | Whether STOP action was called after this step |

#### Metadata

| Field | Type | Recommended | Description |
|-------|------|-------------|-------------|
| `agent_name` | string | Yes | Your method/model name |
| `timestamp` | string | Yes | Generation time (ISO 8601 format) |
| `split` | string | Yes | Always "test" |

---

## Validation Rules

Submissions will undergo the following checks:

### 1. Structural Validation
- ✓ File is valid JSON
- ✓ Root element contains `episodes` field of type array
- ✓ Each episode contains all required fields

### 2. Field Validation
- ✓ `episode_id`, `trajectory_id`, `scene_id` are all strings
- ✓ `actions` is an integer array, each action ∈ {0, 1, 2, 3}
- ✓ Trajectory length 1 ≤ len(actions) ≤ 500

### 3. Data Integrity
- ✓ episode_id comes from test set (no duplicates)
- ✓ Each episode_id appears only once (no duplicate submissions)
- ✓ All episodes from test set are covered

### 4. Optional Field Validation
- If `trajectory` is provided:
  - Length must be ≥ 1 (at least initial state)
  - Each point's position is a float array of length 3
  - heading range [-π, π]
  - stop is boolean

---

## Examples

### Minimal Example (Actions Only)

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [1, 1, 1, 2, 2, 0]
    },
    {
      "episode_id": "1",
      "trajectory_id": "1234",
      "scene_id": "mp3d/GLvvgkT4dwJ/GLvvgkT4dwJ.glb",
      "actions": [3, 1, 0]
    }
  ],
  "metadata": {
    "agent_name": "SimpleAgent",
    "split": "test"
  }
}
```

### Complete Example (With Trajectory)

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [1, 1, 0],
      "trajectory": [
        {
          "position": [6.307, 0.121, 0.185],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.407],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.629],
          "heading": -0.259,
          "stop": true
        }
      ]
    }
  ],
  "metadata": {
    "agent_name": "HA-VLN-CMA",
    "timestamp": "2026-03-31T14:32:15Z",
    "split": "test"
  }
}
```

---

## How to Generate Submission from Your Agent

### 1. Collect Action Sequences
During inference on the test split, record the action sequence for each episode. Here's a template for integrating with your agent:

```python
import json
import gzip
from typing import List, Dict, Any

class SubmissionGenerator:
    def __init__(self):
        self.episodes = []
        
    def add_episode(self, episode_id: str, trajectory_id: str, 
                   scene_id: str, actions: List[int],
                   trajectory: List[Dict] = None):
        """Add an episode to the submission"""
        episode = {
            "episode_id": str(episode_id),
            "trajectory_id": str(trajectory_id),
            "scene_id": scene_id,
            "actions": actions
        }
        if trajectory is not None:
            episode["trajectory"] = trajectory
        self.episodes.append(episode)
    
    def save(self, output_path: str, agent_name: str):
        """Save submission to JSON file"""
        submission = {
            "episodes": self.episodes,
            "metadata": {
                "agent_name": agent_name,
                "timestamp": datetime.now().isoformat(),
                "split": "test"
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(submission, f, indent=2)
```

### 2. Integration with HA-VLN Agent
If you're using the HA-VLN framework, modify your evaluation loop to collect actions:

```python
from challenge.tools.submission_generator import SubmissionGenerator

# Initialize generator
submission_gen = SubmissionGenerator()

# In your evaluation loop
for episode in test_episodes:
    actions = []
    trajectory = []  # Optional: collect positions and headings
    
    env.reset()
    while not env.episode_over:
        # Get action from your agent
        action = agent.act(observation)
        actions.append(action)
        
        # Optional: record trajectory
        state = env.get_agent_state()
        trajectory.append({
            "position": state.position.tolist(),
            "heading": state.rotation,
            "stop": (action == 0)
        })
        
        # Step environment
        observation = env.step(action)
    
    # Add to submission
    submission_gen.add_episode(
        episode_id=episode.episode_id,
        trajectory_id=episode.trajectory_id,
        scene_id=episode.scene_id,
        actions=actions,
        trajectory=trajectory  # Optional
    )

# Save submission
submission_gen.save("my_submission.json", "MyAgent")
```

### 3. Using the Provided Template
A complete template script is available at `challenge/tools/generate_submission.py`. You can adapt it to your agent's interface.

---

## Evaluation Process

1. **Validation**: Check file format and completeness
2. **Replay**: Replay action sequences in private HA-VLN simulator with human rendering enabled
3. **Calculation**: Compute NE, SR, TCR, CR metrics using ground truth data
4. **Aggregation**: Compute dataset-wide averages and statistics
5. **Reporting**: Generate leaderboard results and per-episode details

Results will be returned in the following forms:

- **Public Leaderboard**: SR, TCR, NE, CR (averaged across test set)
- **Diagnostic Statistics**: Per-episode JSON with complete metrics
- **Leaderboard Ranking**:
  1. Primary: SR (Success Rate)
  2. Secondary: TCR (lower is better)
  3. Tertiary: NE (lower is better)

---

## Frequently Asked Questions (FAQ)

**Q: Can I submit trajectories of different lengths?**  
A: Yes. Each episode's action sequence can have different length, but total length cannot exceed 500 steps. The last action should typically be STOP.

**Q: What if I forget to add STOP at the end?**  
A: The evaluator will automatically detect if an episode ends after 500 steps. If no STOP is received, it will be treated as episode_over=False, which may result in lower scores.

**Q: Is the trajectory field optional?**  
A: Yes. Providing trajectory helps with auditing and visualization. If provided, the evaluator will check its consistency with actions.

**Q: Are action codes fixed?**  
A: Yes. Please strictly use the codes in the table above. Other values will trigger validation errors.

**Q: What precision is required for trajectory coordinates?**  
A: We recommend 3 decimal places. The evaluator is not sensitive to floating-point precision, but excessive rounding may affect visualization.

**Q: How do I get the test episode IDs?**  
A: Load `Data/HA-R2R/test/test.json.gz` to see all test episodes with their IDs, scene IDs, and instructions.

**Q: Can I submit partial results?**  
A: No. You must submit predictions for all episodes in the test set (3408 episodes).

---

## Submission Checklist

- [ ] File is valid JSON
- [ ] All required fields are assigned
- [ ] episode_id and scene_id match test.json.gz
- [ ] Each actions element ∈ {0, 1, 2, 3}
- [ ] actions length ≤ 500
- [ ] No duplicate episode_id
- [ ] split field in metadata is "test"
- [ ] (Optional) If trajectory is provided, its fields match the specification

---

**Submission Deadline**: See challenge announcement  
**Evaluation Results**: Typically available within 2 hours  
**Appeal Period**: 7 days after results are published

## Related Documentation

- [Environment Setup](record_env.md) - How to set up the HA-VLN environment
- [Simulator API](record_api.md) - HA-VLN simulator interfaces
- [Agent Integration](record_agent.md) - How to integrate your agent with HA-VLN
- [Challenge Details](record_challenge.md) - Data splits and challenge organization