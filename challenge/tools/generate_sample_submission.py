#!/usr/bin/env python3
"""
HA-VLN Challenge Sample Submission Generator

Generates sample submission files for testing and baseline agents.
Usage: python generate_sample_submission.py --type random --output random_baseline.json
"""

import json
import gzip
import random
import argparse
from datetime import datetime
from typing import List, Dict, Any
import os

# Constants
VALID_ACTIONS = [0, 1, 2, 3]  # STOP, MOVE_FORWARD, TURN_LEFT, TURN_RIGHT
MAX_STEPS = 500
MIN_STEPS = 1


def load_test_episodes(test_path: str) -> List[Dict[str, Any]]:
    """Load test split episodes"""
    if not os.path.exists(test_path):
        raise FileNotFoundError(f"Test file not found: {test_path}")
    
    try:
        if test_path.endswith('.gz'):
            with gzip.open(test_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(test_path, 'r') as f:
                data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load test file: {e}")
    
    return data.get("episodes", [])


def generate_random_actions(min_len: int = 10, max_len: int = 100) -> List[int]:
    """Generate random action sequence"""
    length = random.randint(min_len, max_len)
    actions = []
    
    # Generate random actions (biased toward forward movement)
    for _ in range(length - 1):
        # Weighted probabilities: forward 60%, turns 15% each, stop 10%
        action = random.choices(
            VALID_ACTIONS,
            weights=[0.1, 0.6, 0.15, 0.15]
        )[0]
        actions.append(action)
    
    # Always end with STOP
    actions.append(0)
    
    return actions


def generate_forward_only_actions(min_len: int = 20, max_len: int = 80) -> List[int]:
    """Generate forward-only action sequence"""
    length = random.randint(min_len, max_len)
    actions = [1] * (length - 1)  # All forward
    actions.append(0)  # End with STOP
    return actions


def generate_il_baseline_actions(min_len: int = 15, max_len: int = 60) -> List[int]:
    """Generate imitation learning baseline actions"""
    length = random.randint(min_len, max_len)
    actions = []
    
    # Simulate more intelligent behavior
    for i in range(length - 1):
        if i % 10 == 0:
            # Turn occasionally
            actions.append(random.choice([2, 3]))
        else:
            # Mostly forward
            actions.append(1)
    
    actions.append(0)  # End with STOP
    return actions


def generate_submission(
    episodes: List[Dict[str, Any]],
    action_generator,
    agent_name: str,
    include_trajectory: bool = False
) -> Dict[str, Any]:
    """Generate submission from episodes using specified action generator"""
    submission_episodes = []
    
    for ep in episodes:
        # Generate actions
        actions = action_generator()
        
        # Ensure length constraints
        if len(actions) > MAX_STEPS:
            actions = actions[:MAX_STEPS]
            actions[-1] = 0  # Ensure ends with STOP
        elif len(actions) < MIN_STEPS:
            actions = [1, 0]  # Minimal valid sequence
        
        # Build episode entry
        episode_entry = {
            "episode_id": str(ep.get("episode_id", "")),
            "trajectory_id": str(ep.get("trajectory_id", "")),
            "scene_id": ep.get("scene_id", ""),
            "actions": actions
        }
        
        # Optional: add trajectory (simulated)
        if include_trajectory:
            trajectory = []
            # Simulate positions (this is just for example, not accurate)
            x, y, z = 0.0, 0.0, 0.0
            heading = 0.0
            
            for i, action in enumerate(actions):
                if action == 1:  # MOVE_FORWARD
                    x += 0.25
                elif action == 2:  # TURN_LEFT
                    heading += 0.261799  # 15 degrees in radians
                elif action == 3:  # TURN_RIGHT
                    heading -= 0.261799
                
                # Normalize heading to [-π, π]
                while heading > 3.141592653589793:
                    heading -= 6.283185307179586
                while heading < -3.141592653589793:
                    heading += 6.283185307179586
                
                trajectory.append({
                    "position": [round(x, 3), round(y, 3), round(z, 3)],
                    "heading": round(heading, 3),
                    "stop": (action == 0)
                })
            
            episode_entry["trajectory"] = trajectory
        
        submission_episodes.append(episode_entry)
    
    # Build complete submission
    submission = {
        "episodes": submission_episodes,
        "metadata": {
            "agent_name": agent_name,
            "timestamp": datetime.now().isoformat(),
            "split": "test"
        }
    }
    
    return submission


def main():
    parser = argparse.ArgumentParser(
        description="Generate sample submission files for HA-VLN Challenge"
    )
    parser.add_argument(
        "--type",
        choices=["random", "forward", "il_baseline"],
        default="random",
        help="Type of baseline agent"
    )
    parser.add_argument(
        "--output",
        default="sample_submission.json",
        help="Output file path"
    )
    parser.add_argument(
        "--test-file",
        default="../Data/HA-R2R/test/test.json.gz",
        help="Path to test split file"
    )
    parser.add_argument(
        "--include-trajectory",
        action="store_true",
        help="Include trajectory data (optional)"
    )
    parser.add_argument(
        "--max-episodes",
        type=int,
        default=None,
        help="Maximum number of episodes to include (for testing)"
    )
    
    args = parser.parse_args()
    
    # Load test episodes
    try:
        print(f"Loading test episodes from {args.test_file}...")
        episodes = load_test_episodes(args.test_file)
        print(f"Loaded {len(episodes)} episodes")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    # Limit episodes for testing
    if args.max_episodes:
        episodes = episodes[:args.max_episodes]
        print(f"Limited to {len(episodes)} episodes")
    
    # Select action generator
    if args.type == "random":
        action_generator = lambda: generate_random_actions()
        agent_name = "RandomBaseline"
    elif args.type == "forward":
        action_generator = lambda: generate_forward_only_actions()
        agent_name = "ForwardOnlyBaseline"
    elif args.type == "il_baseline":
        action_generator = lambda: generate_il_baseline_actions()
        agent_name = "ILBaseline"
    else:
        print(f"Unknown agent type: {args.type}")
        return 1
    
    # Generate submission
    print(f"Generating {args.type} submission...")
    submission = generate_submission(
        episodes=episodes,
        action_generator=action_generator,
        agent_name=agent_name,
        include_trajectory=args.include_trajectory
    )
    
    # Save to file
    print(f"Saving to {args.output}...")
    with open(args.output, 'w') as f:
        json.dump(submission, f, indent=2)
    
    # Validate the generated file
    print("Validating generated submission...")
    try:
        # Simple validation
        with open(args.output, 'r') as f:
            data = json.load(f)
        
        episodes_count = len(data.get("episodes", []))
        print(f"✓ Generated {episodes_count} episodes")
        
        # Check a few random episodes
        for i in range(min(3, episodes_count)):
            ep = data["episodes"][i]
            actions = ep.get("actions", [])
            print(f"  Episode {ep['episode_id']}: {len(actions)} actions, "
                  f"last action: {actions[-1] if actions else 'N/A'}")
        
        print(f"\n✓ Submission generated successfully!")
        print(f"  Agent: {agent_name}")
        print(f"  Episodes: {episodes_count}")
        print(f"  Trajectory included: {args.include_trajectory}")
        
    except Exception as e:
        print(f"Warning: Validation failed: {e}")
    
    return 0


if __name__ == "__main__":
    exit(main())