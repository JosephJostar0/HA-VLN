# HA-VLN Challenge

Welcome to the HA-VLN (Human-Aware Vision-and-Language Navigation) Challenge! This challenge evaluates agents' ability to navigate in dynamic human-populated environments while following natural language instructions.

## Quick Links

- [Submission Format](SUBMISSION_FORMAT.md) - Detailed specification for submission files
- [Environment Setup](../record_env.md) - How to set up the HA-VLN environment
- [Simulator API](../record_api.md) - HA-VLN simulator interfaces
- [Agent Integration](../record_agent.md) - How to integrate your agent with HA-VLN
- [Challenge Details](../record_challenge.md) - Data splits and challenge organization

## Challenge Overview

### Task Description
The HA-VLN challenge requires agents to navigate from a starting position to a goal location in indoor environments populated with dynamic human activities. Agents must follow natural language instructions that describe both the path and human activities (e.g., "pass by a person talking on the phone").

### Key Features
- **Dynamic Human Activities**: Real-time rendering of human motions and interactions
- **Complex Instructions**: Natural language descriptions incorporating human behaviors
- **Human-Aware Evaluation**: Metrics that account for collision avoidance and social navigation

## Getting Started

### 1. Set Up Environment
Follow the [Environment Setup](../record_env.md) guide to install all dependencies.

### 2. Download Data
```bash
# Download HA-R2R and HAPS 2.0 datasets
bash scripts/download_data.sh

# Download test split (non-GT version for participants)
# This is included in the download_data.sh script
```

### 3. Train Your Agent
Use the provided baseline agents or implement your own:

```bash
cd agent
# Train HA-VLN-CMA baseline
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type train

# Evaluate on validation splits
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type eval
```

### 4. Generate Submission
Run inference on the test split and generate submission file:

```bash
# Run inference (you'll need to modify to collect actions)
python run.py --exp-config config/cma_pm_da_aug_tune.yaml --run-type inference

# Use the submission template to format your results
python challenge/tools/generate_submission.py --help
```

## Evaluation Metrics

The challenge uses four core metrics:

1. **Navigation Error (NE)**: Mean distance between agent's final position and goal
2. **Success Rate (SR)**: Percentage of episodes completed successfully with zero collisions
3. **Total Collision Rate (TCR)**: Average collisions in human-occupied zones
4. **Collision Rate (CR)**: Percentage of episodes with at least one collision

See the [paper](https://arxiv.org/abs/2503.14229) for detailed metric definitions.

## Submission Process

### 1. Prepare Your Submission
Your submission must be a JSON file following the [Submission Format](SUBMISSION_FORMAT.md). Key requirements:
- Include all 3408 test episodes
- Each episode must have 1-500 actions
- Actions must use codes: 0=STOP, 1=MOVE_FORWARD, 2=TURN_LEFT, 3=TURN_RIGHT

### 2. Validate Your Submission
Use the provided validation script:
```bash
python challenge/tools/validate_submission.py my_submission.json
```

### 3. Submit
Submit your JSON file through the designated submission portal (to be announced).

## Timeline

- **Training Phase**: Participants develop and train agents using train/val splits
- **Submission Phase**: Participants submit predictions for test split
- **Evaluation Phase**: Organizers evaluate submissions and compute metrics
- **Results Announcement**: Leaderboard published with rankings

## Baseline Agents

The challenge provides several baseline agents:

1. **Random Agent**: Selects random actions
2. **Forward-Only Agent**: Always moves forward until max steps
3. **HA-VLN-CMA**: Cross-Model Attention agent (state-of-the-art baseline)

Example submissions for these baselines are available in `challenge/examples/`.

## Resources

### Datasets
- **HA-R2R**: Human-Aware Room-to-Room dataset with complex instructions
- **HAPS 2.0**: Human Activity and Pose Simulation dataset with 3D human motions
- **Matterport3D**: 90 indoor scenes for navigation

### Code
- **HA-VLN Simulator**: Real-time human rendering and navigation
- **Baseline Agents**: Reference implementations
- **Evaluation Tools**: Validation and submission utilities

### Documentation
- [Technical Paper](https://arxiv.org/abs/2503.14229)
- [Project Website](https://ha-vln-project.vercel.app/)
- [GitHub Repository](https://github.com/F1y1113/HA-VLN)

## Support

For questions about the challenge:
- Check the [FAQ](SUBMISSION_FORMAT.md#frequently-asked-questions-faq)
- Review existing documentation
- Open an issue on the GitHub repository

## Important Notes

- **Test Ground Truth**: The test split ground truth (`test_gt.json.gz`) is kept private by organizers
- **Fairness**: All submissions are evaluated on the same private test set
- **Reproducibility**: Participants should document their methods for reproducibility
- **Code Release**: Winners may be asked to release code for verification

---

**Good luck with the challenge!**