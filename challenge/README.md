# HA-VLN Challenge System

Complete automatic scoring and evaluation system for the HA-VLN challenge.

## 📋 Overview

This system provides:

1. **Submission Format Specification** - Exactly how to format submissions
2. **Automatic Evaluator** - Validates, replays, and scores submissions
3. **Documentation** - Complete guides for participants
4. **Starter Kit** - Templates and examples to get started
5. **Configuration** - Centralized parameter management

## 📁 Directory Structure

```
challenge/
├── README.md                      # ← You are here
├── SUBMISSION_FORMAT.md           # Required submission schema
├── EVALUATION_GUIDE.md            # How evaluation works, interpretation
├── STARTER_KIT.md                 # Getting started guide
│
├── evaluator.py                   # Main evaluation script (5 stages)
├── template_solution.py           # Solution template for development
├── config.json                    # Evaluator configuration
│
├── examples/                      # Example submissions
│   ├── random_baseline.json
│   ├── forward_walk.json
│   └── il_baseline.json
│
└── [eval_results/]               # Created after running evaluator
    ├── leaderboard.json          # Public metrics
    ├── per_episode.json          # Per-episode scores
    ├── aggregated.json           # Full statistics
    └── summary.txt               # Human-readable report
```

## 🚀 Quick Start

### For Participants

1. **Understand the format**:
   ```bash
   cat SUBMISSION_FORMAT.md
   ```

2. **Review examples**:
   ```bash
   ls -lh examples/
   ```

3. **Develop your solution**:
   ```bash
   python template_solution.py --policy forward --output my_submission.json
   ```

4. **Test locally** (if evaluator available):
   ```bash
   python evaluator.py my_submission.json
   ```

### For Organizers

1. **Run evaluation**:
   ```bash
   python evaluator.py submission.json --output results/
   ```

2. **Check results**:
   ```bash
   cat results/leaderboard.json
   cat results/summary.txt
   ```

3. **Analyze per-episode**:
   ```python
   import json
   with open("results/per_episode.json") as f:
       episodes = json.load(f)
   ```

## 📝 File Descriptions

### Core Files

| File | Purpose | Audience |
|------|---------|----------|
| SUBMISSION_FORMAT.md | JSON schema specification | All participants |
| EVALUATION_GUIDE.md | How evaluation works & metric interpretation | All participants |
| STARTER_KIT.md | Development guide with templates | Developers |
| evaluator.py | Main 5-stage evaluation pipeline | Organizers |
| config.json | Evaluation parameters & paths | Organizers |

### Supporting Files

| File | Purpose |
|------|---------|
| template_solution.py | Starting point for solution development |
| examples/ | Reference submissions (3 examples) |

## 🔧 Configuration

Edit `config.json` to customize:

```json
{
  "paths": {
    "test_path": "Data/HA-R2R/test.json.gz",
    "test_gt_path": "Data/HA-R2R/test_gt.json.gz",
    "collision_stats_path": "Data/HA-R2R-tools/collision_num_{split}.json"
  },
  "parameters": {
    "success_distance": 3.0,      // Goal reached threshold (m)
    "forward_step_size": 0.25,    // Distance per MOVE_FORWARD (m)
    "turn_angle": 15              // Angle per turn (degrees)
  }
}
```

## 📊 Evaluation Stages

### Stage 1: Submission Validator
- Checks JSON structure
- Validates all required fields
- Verifies action codes [0-3]
- Checks episode count
- **Output**: Pass/Fail + error messages

### Stage 2: Action Replayer
- Loads GT data
- Simulates agent movement for each action sequence
- Records trajectory positions
- **Output**: Simulated 3D trajectories

### Stage 3: Metric Engine
- Computes Success (SR)
- Computes Path Length and SPL (efficiency)
- Computes nDTW (path alignment)
- Computes sDTW (success-weighted alignment)
- Computes collisions, TCR, CR, SR_human (human-aware)
- **Output**: Per-episode metrics

### Stage 4: Aggregator
- Computes mean/std/min/max for each metric
- Aggregates across all episodes
- **Output**: Summary statistics

### Stage 5: Reporter
- Generates public leaderboard metrics
- Saves per-episode details
- Creates human-readable summary
- **Output**: JSON reports + summary

## 📈 Metrics Explained

### Public Leaderboard (ranked by)

1. **SR_human** - Success Rate (Human-Aware)
   - Primary metric
   - Requires both: reaching goal AND avoiding excess collisions
   - Range: [0, 1]

2. **SPL** - Success-weighted Path Length
   - Efficiency metric
   - Rewards reaching goal with short paths
   - Range: [0, 1]

3. **nDTW** - Normalized Dynamic Time Warping
   - Path alignment to reference
   - Range: [0, 1]

### Additional Metrics (detailed results)

- **Success**: Binary goal reached
- **Collisions**: Human collision count
- **TCR**: Total Corrective Reward
- **sDTW**: Success-weighted DTW

See EVALUATION_GUIDE.md for full descriptions.

## ✅ Submission Requirements

### Format
- JSON file with `episodes` array
- One entry per test episode (3408 total)
- Each entry: `episode_id`, `trajectory_id`, `scene_id`, `actions`

### Actions
- Array of integers: 0 (STOP), 1 (FORWARD), 2 (LEFT), 3 (RIGHT)
- Must end with STOP (0)
- Between 1-500 actions per episode

### Validation
- No duplicate episode_ids
- All episodes from official test split
- Valid action codes only
- Proper JSON structure

See SUBMISSION_FORMAT.md for examples and detailed rules.

## 🎯 Development Workflow

### Step 1: Understand
```bash
cat SUBMISSION_FORMAT.md        # Format spec
cat EVALUATION_GUIDE.md         # How it works
ls examples/                    # See examples
```

### Step 2: Develop
```bash
# Start from template
python template_solution.py --policy forward --output v1.json

# Or integrate with your model
# (See template_solution.py for integration points)
```

### Step 3: Validate
```bash
# Check JSON structure
python -c "import json; f=open('v1.json'); json.load(f); print('OK')"

# Check episode count
python -c "import json; f=open('v1.json'); d=json.load(f); print(f'Episodes: {len(d[\"episodes\"])}')"
```

### Step 4: Evaluate (organizers)
```bash
python evaluator.py v1.json --output results_v1/
cat results_v1/summary.txt
python -c "import json; print(json.dumps(json.load(open('results_v1/leaderboard.json')), indent=2))"
```

### Step 5: Iterate
- Analyze results
- Improve model
- Generate new submission
- Re-evaluate

## 🐛 Troubleshooting

### Submission Validation Fails
- **Check**: SUBMISSION_FORMAT.md for exact schema
- **Check**: examples/ for correct structure
- **Check**: All 3408 test episodes present
- **Check**: Action codes are integers [0-3]

### Metrics Don't Make Sense
- **Check**: EVALUATION_GUIDE.md "Interpreting Results"
- **Check**: per_episode.json for specific failing episodes
- **Check**: Examples in STARTER_KIT.md

### Evaluator Crashes
- **Check**: config.json paths are correct
- **Check**: test_gt.json.gz exists and readable
- **Check**: Working directory is workspace root

## 📖 Documentation Map

```
Getting Started:
  → SUBMISSION_FORMAT.md
  → examples/

Understanding Evaluation:
  → EVALUATION_GUIDE.md
  → evaluator.py (code comments)

Developing Solutions:
  → STARTER_KIT.md
  → template_solution.py
  → examples/

Managing Challenge:
  → config.json
  → EVALUATION_GUIDE.md "Running the Evaluator"
```

## 🔐 Data Privacy

### Test Data Splits

- **test.json.gz** (public)
  - Episode metadata, instructions, reference paths
  - NO goals (prevents local scoring)
  - Participants have full access

- **test_gt.json.gz** (private, organizers only)
  - Contains goals and complete reference paths
  - Used only by evaluator for scoring
  - Not shared with participants

- **collision_num_test.json** (private, organizers only)
  - Baseline collision statistics
  - Used for TCR computation
  - Prevents gaming the human-aware metric

This design prevents:
- Local cheating via memorization
- Leaderboard overfitting
- Metric gaming

## 📞 Support

### For Participants
1. Read SUBMISSION_FORMAT.md (format questions)
2. Read EVALUATION_GUIDE.md (metric questions)
3. Review examples/ (format examples)
4. Check STARTER_KIT.md (development help)

### For Organizers
1. Check evaluator.py code comments
2. Verify config.json paths
3. Review EVALUATION_GUIDE.md "Running the Evaluator"
4. Check troubleshooting section

## 📝 License

See LICENSE file in repository root.

## 🎓 Citation

If using this evaluation system in a paper:
```bibtex
@misc{havln_challenge,
  title={HA-VLN Challenge Evaluation System},
  year={2024},
  organization={HA-VLN Team}
}
```

## Version History

- **v1.0** (2024-01-15)
  - Initial 5-stage evaluation system
  - Support for classic VLN + human-aware metrics
  - Full documentation and starter kit

---

**Last Updated**: 2024-01-15  
**Maintained By**: HA-VLN Challenge Team
