#!/usr/bin/env python3
"""
HA-VLN Challenge Submission Validator

Validates submission files against the format specification.
Usage: python validate_submission.py <submission.json>
"""

import json
import sys
import os
import gzip
from typing import Set, Dict, Any, List, Optional
import argparse

# Constants from specification
VALID_ACTIONS = {0, 1, 2, 3}
MIN_ACTIONS = 1
MAX_ACTIONS = 500


class SubmissionValidator:
    """Validates submission format and completeness"""
    
    def __init__(self, test_episode_ids: Optional[Set[str]] = None):
        """
        Args:
            test_episode_ids: Set of valid episode IDs from test split.
                              If None, skips episode ID validation.
        """
        self.test_episode_ids = test_episode_ids
        self.errors = []
        self.warnings = []
    
    def validate_file(self, filepath: str) -> bool:
        """Validate a submission file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Error reading file: {e}")
            return False
        
        return self.validate_structure(data)
    
    def validate_structure(self, data: Dict[str, Any]) -> bool:
        """Validate submission data structure"""
        self.errors = []
        self.warnings = []
        
        # Check root structure
        if not isinstance(data, dict):
            self.errors.append("Root element must be a dictionary")
            return False
        
        if "episodes" not in data:
            self.errors.append("Missing 'episodes' field in root")
            return False
        
        episodes = data.get("episodes", [])
        if not isinstance(episodes, list):
            self.errors.append("'episodes' field must be an array")
            return False
        
        if len(episodes) == 0:
            self.errors.append("'episodes' array is empty")
            return False
        
        # Validate each episode
        seen_episode_ids = set()
        for i, ep_data in enumerate(episodes):
            self._validate_episode(ep_data, i, seen_episode_ids)
        
        # Check coverage if test IDs are provided
        if self.test_episode_ids:
            missing_episodes = self.test_episode_ids - seen_episode_ids
            if missing_episodes:
                missing_list = sorted(list(missing_episodes))[:10]
                self.warnings.append(
                    f"Missing {len(missing_episodes)} episodes from test set. "
                    f"First few: {missing_list}..."
                )
        
        # Check metadata
        metadata = data.get("metadata", {})
        if not metadata:
            self.warnings.append("Missing 'metadata' field (optional but recommended)")
        else:
            if "agent_name" not in metadata:
                self.warnings.append("metadata should include 'agent_name'")
            if "split" in metadata and metadata["split"] != "test":
                self.warnings.append(f"metadata.split should be 'test', got '{metadata['split']}'")
        
        return len(self.errors) == 0
    
    def _validate_episode(self, ep_data: Dict, index: int, seen_ids: Set[str]):
        """Validate a single episode"""
        
        # Check required fields
        required_fields = ["episode_id", "trajectory_id", "scene_id", "actions"]
        ep_id = ep_data.get("episode_id", f"unknown_{index}")
        
        for field in required_fields:
            if field not in ep_data:
                self.errors.append(f"Episode {index}: Missing field '{field}'")
                return
        
        # Type checks
        if not isinstance(ep_data["episode_id"], str):
            self.errors.append(f"Episode {index}: episode_id must be string")
        if not isinstance(ep_data["trajectory_id"], str):
            self.errors.append(f"Episode {index}: trajectory_id must be string")
        if not isinstance(ep_data["scene_id"], str):
            self.errors.append(f"Episode {index}: scene_id must be string")
        if not isinstance(ep_data["actions"], list):
            self.errors.append(f"Episode {ep_id}: actions must be array")
            return
        
        # Check episode_id validity
        if self.test_episode_ids and ep_id not in self.test_episode_ids:
            self.errors.append(f"Episode {ep_id}: Not found in test split")
        
        # Check for duplicates
        if ep_id in seen_ids:
            self.errors.append(f"Episode {ep_id}: Duplicate episode_id")
        seen_ids.add(ep_id)
        
        # Validate actions
        actions = ep_data["actions"]
        if not (MIN_ACTIONS <= len(actions) <= MAX_ACTIONS):
            self.errors.append(
                f"Episode {ep_id}: Action count {len(actions)} not in "
                f"[{MIN_ACTIONS}, {MAX_ACTIONS}]"
            )
        
        for i, action in enumerate(actions):
            if not isinstance(action, int):
                self.errors.append(
                    f"Episode {ep_id}, step {i}: action must be int, "
                    f"got {type(action).__name__}"
                )
            elif action not in VALID_ACTIONS:
                self.errors.append(
                    f"Episode {ep_id}, step {i}: invalid action code {action}, "
                    f"valid: {sorted(VALID_ACTIONS)}"
                )
        
        # Optional: validate trajectory if provided
        if "trajectory" in ep_data:
            self._validate_trajectory(ep_data, ep_id)
    
    def _validate_trajectory(self, ep_data: Dict, ep_id: str):
        """Validate optional trajectory field"""
        traj = ep_data.get("trajectory")
        if not isinstance(traj, list):
            self.warnings.append(f"Episode {ep_id}: trajectory must be array")
            return
        
        if len(traj) < 1:
            self.warnings.append(f"Episode {ep_id}: trajectory is empty")
            return
        
        for i, point in enumerate(traj):
            if not isinstance(point, dict):
                self.warnings.append(f"Episode {ep_id}, trajectory[{i}]: must be dict")
                continue
            
            # Check position
            if "position" in point:
                pos = point["position"]
                if not isinstance(pos, list) or len(pos) != 3:
                    self.warnings.append(
                        f"Episode {ep_id}, trajectory[{i}]: position must be "
                        f"[x, y, z], got {pos}"
                    )
                elif not all(isinstance(p, (int, float)) for p in pos):
                    self.warnings.append(
                        f"Episode {ep_id}, trajectory[{i}]: position values "
                        f"must be numeric"
                    )
            
            # Check heading
            if "heading" in point:
                heading = point["heading"]
                if not isinstance(heading, (int, float)):
                    self.warnings.append(
                        f"Episode {ep_id}, trajectory[{i}]: heading must be float"
                    )
                elif not (-3.141592653589793 <= heading <= 3.141592653589793):  # -π to π
                    self.warnings.append(
                        f"Episode {ep_id}, trajectory[{i}]: heading {heading} "
                        f"outside [-π, π]"
                    )
            
            # Check stop
            if "stop" in point and not isinstance(point["stop"], bool):
                self.warnings.append(
                    f"Episode {ep_id}, trajectory[{i}]: stop must be boolean"
                )
    
    def get_report(self) -> str:
        """Get validation report"""
        lines = []
        
        if self.errors:
            lines.append("=== ERRORS ===")
            for err in self.errors:
                lines.append(f"✗ {err}")
        
        if self.warnings:
            lines.append("\n=== WARNINGS ===")
            for warn in self.warnings:
                lines.append(f"⚠ {warn}")
        
        if not self.errors and not self.warnings:
            lines.append("✓ Submission is valid!")
        elif not self.errors:
            lines.append("\n✓ Submission is valid (with warnings)")
        else:
            lines.append(f"\n✗ Submission has {len(self.errors)} error(s)")
        
        return "\n".join(lines)


def load_test_episode_ids(test_path: str) -> Optional[Set[str]]:
    """Load test split and extract valid episode IDs"""
    if not os.path.exists(test_path):
        print(f"Warning: Test file not found: {test_path}")
        return None
    
    try:
        if test_path.endswith('.gz'):
            with gzip.open(test_path, 'rt', encoding='utf-8') as f:
                data = json.load(f)
        else:
            with open(test_path, 'r') as f:
                data = json.load(f)
    except Exception as e:
        print(f"Warning: Failed to load test file: {e}")
        return None
    
    episode_ids = set()
    for ep in data.get("episodes", []):
        episode_ids.add(str(ep.get("episode_id")))
    
    return episode_ids


def main():
    parser = argparse.ArgumentParser(
        description="Validate HA-VLN Challenge submission"
    )
    parser.add_argument(
        "submission",
        help="Path to submission JSON file"
    )
    parser.add_argument(
        "--test-file",
        default="../Data/HA-R2R/test/test.json.gz",
        help="Path to test split file for episode ID validation"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    
    args = parser.parse_args()
    
    # Load test episode IDs
    test_episode_ids = load_test_episode_ids(args.test_file)
    
    # Validate submission
    validator = SubmissionValidator(test_episode_ids)
    
    if not validator.validate_file(args.submission):
        print("Failed to load submission file")
        sys.exit(1)
    
    # Print report
    report = validator.get_report()
    print(report)
    
    # Exit code
    if validator.errors:
        sys.exit(1)
    elif args.strict and validator.warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()