#!/usr/bin/env python3
"""
HA-VLN Challenge Automatic Evaluator

Five-stage evaluation pipeline:
1. Submission Validator - Validates submission format
2. Replayer - Replays actions in simulator
3. Metric Engine - Computes metrics
4. Aggregator - Aggregates results
5. Reporter - Generates leaderboard and per-episode reports
"""

import gzip
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging
import argparse
from datetime import datetime
from dataclasses import dataclass, asdict

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Stage 1: Submission Validator
# ============================================================================

@dataclass
class ValidationError:
    """Represents a validation error"""
    episode_id: str
    error_type: str
    message: str
    severity: str = "error"  # "error" or "warning"


class SubmissionValidator:
    """Validates submission format and completeness"""
    
    VALID_ACTIONS = {0, 1, 2, 3}
    MIN_ACTIONS = 1
    MAX_ACTIONS = 500
    
    ACTION_NAMES = {
        0: "STOP",
        1: "MOVE_FORWARD",
        2: "TURN_LEFT",
        3: "TURN_RIGHT"
    }
    
    def __init__(self, test_episode_ids: set):
        """
        Args:
            test_episode_ids: Set of valid episode IDs from test split
        """
        self.test_episode_ids = test_episode_ids
        self.errors = []
        self.warnings = []
    
    def validate(self, submission_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate submission data
        
        Returns:
            (is_valid, error_messages)
        """
        self.errors = []
        self.warnings = []
        
        # Check root structure
        if not isinstance(submission_data, dict):
            self.errors.append("Root element must be a dict")
            return False, self._format_errors()
        
        if "episodes" not in submission_data:
            self.errors.append("Missing 'episodes' field in root")
            return False, self._format_errors()
        
        episodes = submission_data.get("episodes", [])
        if not isinstance(episodes, list):
            self.errors.append("'episodes' field must be an array")
            return False, self._format_errors()
        
        if len(episodes) == 0:
            self.errors.append("'episodes' array is empty")
            return False, self._format_errors()
        
        # Validate each episode
        seen_episode_ids = set()
        for i, ep_data in enumerate(episodes):
            self._validate_episode(ep_data, i, seen_episode_ids)
        
        # Check coverage
        missing_episodes = self.test_episode_ids - seen_episode_ids
        if missing_episodes:
            self.warnings.append(
                f"Missing {len(missing_episodes)} episodes from test set: "
                f"{sorted(list(missing_episodes))[:10]}..."
            )
        
        is_valid = len(self.errors) == 0
        return is_valid, self._format_errors()
    
    def _validate_episode(self, ep_data: Dict, index: int, seen_ids: set):
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
        if ep_id not in self.test_episode_ids:
            self.errors.append(
                f"Episode {ep_id}: Not found in test split"
            )
        
        # Check for duplicates
        if ep_id in seen_ids:
            self.errors.append(
                f"Episode {ep_id}: Duplicate episode_id"
            )
        seen_ids.add(ep_id)
        
        # Validate actions
        actions = ep_data["actions"]
        if not (self.MIN_ACTIONS <= len(actions) <= self.MAX_ACTIONS):
            self.errors.append(
                f"Episode {ep_id}: Action count {len(actions)} not in "
                f"[{self.MIN_ACTIONS}, {self.MAX_ACTIONS}]"
            )
        
        for i, action in enumerate(actions):
            if not isinstance(action, int):
                self.errors.append(
                    f"Episode {ep_id}, step {i}: action must be int, "
                    f"got {type(action).__name__}"
                )
            elif action not in self.VALID_ACTIONS:
                self.errors.append(
                    f"Episode {ep_id}, step {i}: invalid action code {action}, "
                    f"valid: {sorted(self.VALID_ACTIONS)}"
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
                self.warnings.append(
                    f"Episode {ep_id}, trajectory[{i}]: must be dict"
                )
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
                        f"Episode {ep_id}, trajectory[{i}]: heading must be "
                        f"float"
                    )
                elif not (-np.pi <= heading <= np.pi):
                    self.warnings.append(
                        f"Episode {ep_id}, trajectory[{i}]: heading {heading} "
                        f"outside [-π, π]"
                    )
    
    def _format_errors(self) -> List[str]:
        """Format errors and warnings for output"""
        messages = []
        for err in self.errors:
            messages.append(f"[ERROR] {err}")
        for warn in self.warnings:
            messages.append(f"[WARNING] {warn}")
        return messages


# ============================================================================
# Stage 2 & 3: Replayer + Metric Engine
# ============================================================================

class EvaluationResult:
    """Stores evaluation result for one episode"""
    
    def __init__(self, episode_id: str):
        self.episode_id = episode_id
        self.success = 0.0
        self.spl = 0.0
        self.path_length = 0.0
        self.oracle_success = 0.0
        self.oracle_spl = 0.0
        self.ndtw = 0.0
        self.sdtw = 0.0
        self.steps = 0
        self.collisions = 0
        self.tcr = 0
        self.cr = 0.0
        self.sr_human = 0.0
        self.distance_to_goal = float('inf')
        self.oracle_distance_to_goal = float('inf')
        self.reference_path_length = 0.0
        
        # Trajectory for visualization
        self.trajectory = []
        self.error_message = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "episode_id": self.episode_id,
            "success": float(self.success),
            "spl": float(self.spl),
            "path_length": float(self.path_length),
            "oracle_success": float(self.oracle_success),
            "oracle_spl": float(self.oracle_spl),
            "ndtw": float(self.ndtw),
            "sdtw": float(self.sdtw),
            "steps": int(self.steps),
            "collisions": int(self.collisions),
            "tcr": int(self.tcr),
            "cr": float(self.cr),
            "sr_human": float(self.sr_human),
            "distance_to_goal": float(self.distance_to_goal),
            "oracle_distance_to_goal": float(self.oracle_distance_to_goal),
            "reference_path_length": float(self.reference_path_length),
            "error": self.error_message
        }


def euclidean_distance(pos_a: np.ndarray, pos_b: np.ndarray) -> float:
    """Compute Euclidean distance between two positions"""
    return float(np.linalg.norm(pos_b - pos_a, ord=2))


def dtw_distance(path1: List[List[float]], path2: List[List[float]]) -> float:
    """Compute DTW distance between two paths using fastdtw or simple DTW"""
    try:
        from fastdtw import fastdtw
        distance, _ = fastdtw(
            path1, path2,
            dist=lambda a, b: euclidean_distance(
                np.array(a), np.array(b)
            )
        )
        return distance
    except ImportError:
        # Fallback to simple DTW
        n, m = len(path1), len(path2)
        dtw = np.full((n + 1, m + 1), np.inf)
        dtw[0, 0] = 0
        
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                cost = euclidean_distance(
                    np.array(path1[i-1]),
                    np.array(path2[j-1])
                )
                dtw[i, j] = cost + min(dtw[i-1, j], dtw[i, j-1],
                                       dtw[i-1, j-1])
        
        return dtw[n, m]


class ChallengeEvaluator:
    """Main evaluator combining Replayer and Metric Engine"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Configuration dict with paths and parameters
        """
        self.config = config
        self.success_distance = config.get("success_distance", 3.0)
        self.forward_step_size = config.get("forward_step_size", 0.25)
        self.turn_angle = config.get("turn_angle", 15)  # degrees
        
        # Load GT data and collision stats
        self._load_ground_truth()
        self._load_collision_stats()
    
    def _load_ground_truth(self):
        """Load test_gt.json.gz"""
        gt_path = self.config.get("test_gt_path")
        if not gt_path or not os.path.exists(gt_path):
            raise FileNotFoundError(f"test_gt not found: {gt_path}")
        
        logger.info(f"Loading GT data from {gt_path}")
        with gzip.open(gt_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        # Index episodes by episode_id
        self.gt_episodes = {}
        for ep in data.get("episodes", []):
            ep_id = str(ep.get("episode_id"))
            self.gt_episodes[ep_id] = ep
        
        logger.info(f"Loaded {len(self.gt_episodes)} GT episodes")
    
    def _load_collision_stats(self):
        """Load collision statistics for split"""
        split = self.config.get("split", "test")
        collision_path = self.config.get("collision_stats_path", "").format(
            split=split
        )
        
        self.baseline_collisions = {}
        if collision_path and os.path.exists(collision_path):
            logger.info(f"Loading collision stats from {collision_path}")
            with open(collision_path, 'r') as f:
                self.baseline_collisions = json.load(f)
        else:
            logger.warning(f"Collision stats not found: {collision_path}")
    
    def evaluate(self, episode_id: str, actions: List[int]) -> EvaluationResult:
        """
        Evaluate one episode
        
        Args:
            episode_id: Episode ID
            actions: List of action codes
        
        Returns:
            EvaluationResult with all metrics
        """
        result = EvaluationResult(episode_id)
        
        # Find GT
        if episode_id not in self.gt_episodes:
            result.error_message = f"Episode not found in GT"
            return result
        
        gt_ep = self.gt_episodes[episode_id]
        
        try:
            # Extract GT data
            start_pos = np.array(gt_ep.get("start_position", [0, 0, 0]))
            goals = gt_ep.get("goals", [])
            if not goals:
                result.error_message = "No goals in GT"
                return result
            
            goal_pos = np.array(goals[0].get("position", [0, 0, 0]))
            
            reference_path = gt_ep.get("reference_path", [])
            ref_path_np = [np.array(p) for p in reference_path]
            
            # Simulate trajectory
            current_pos = start_pos.copy()
            current_heading = 0.0  # Assume initial heading is 0
            
            trajectory = [current_pos.copy()]
            path_positions = [current_pos.copy()]
            collisions_count = 0
            steps_taken = 0
            stopped = False
            
            for action in actions:
                steps_taken += 1
                
                if action == 0:  # STOP
                    stopped = True
                    break
                elif action == 1:  # MOVE_FORWARD
                    # Simulate forward movement (simplified)
                    move_vec = np.array([
                        np.sin(current_heading),
                        0,
                        np.cos(current_heading)
                    ]) * self.forward_step_size
                    current_pos = current_pos + move_vec
                    # Simple collision detection (disabled for now)
                    # collisions_count += check_collision(current_pos)
                elif action == 2:  # TURN_LEFT
                    current_heading += np.deg2rad(self.turn_angle)
                elif action == 3:  # TURN_RIGHT
                    current_heading -= np.deg2rad(self.turn_angle)
                
                trajectory.append(current_pos.copy())
                if action == 1:  # Record position only on movement
                    path_positions.append(current_pos.copy())
            
            result.trajectory = [p.tolist() for p in trajectory]
            result.steps = steps_taken
            result.collisions = collisions_count
            
            # Compute metrics
            distance_to_goal = euclidean_distance(current_pos, goal_pos)
            result.distance_to_goal = distance_to_goal
            result.success = 1.0 if distance_to_goal <= self.success_distance else 0.0
            
            # Path length
            path_length = 0.0
            for i in range(1, len(path_positions)):
                path_length += euclidean_distance(
                    path_positions[i],
                    path_positions[i-1]
                )
            result.path_length = path_length
            
            # Compute reference path length
            if ref_path_np:
                ref_length = 0.0
                for i in range(1, len(ref_path_np)):
                    ref_length += euclidean_distance(
                        ref_path_np[i],
                        ref_path_np[i-1]
                    )
                result.reference_path_length = ref_length
            
            # SPL = success * ref_path_length / max(ref_path_length, path_length)
            if result.reference_path_length > 0:
                result.spl = result.success * (
                    result.reference_path_length /
                    max(result.reference_path_length, path_length)
                )
            
            # Oracle metrics
            oracle_distance = float('inf')
            for pos in path_positions:
                d = euclidean_distance(pos, goal_pos)
                oracle_distance = min(oracle_distance, d)
            result.oracle_distance_to_goal = oracle_distance
            result.oracle_success = 1.0 if oracle_distance <= self.success_distance else 0.0
            
            if result.reference_path_length > 0:
                result.oracle_spl = result.oracle_success * (
                    result.reference_path_length /
                    max(result.reference_path_length, path_length)
                )
            
            # nDTW and sDTW
            if ref_path_np:
                dtw_dist = dtw_distance(path_positions, ref_path_np)
                norm_factor = len(ref_path_np) * self.success_distance
                result.ndtw = np.exp(-dtw_dist / max(norm_factor, 1.0))
                result.sdtw = result.success * result.ndtw
            
            # Human-aware metrics
            baseline = self.baseline_collisions.get(str(episode_id), 0)
            result.tcr = max(0, result.collisions - baseline)
            result.cr = min(result.tcr, 1)
            result.sr_human = result.success * (1.0 if result.tcr == 0 else 0.0)
            
        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Error evaluating episode {episode_id}: {e}")
        
        return result


# ============================================================================
# Stage 4: Aggregator
# ============================================================================

class ResultAggregator:
    """Aggregates per-episode results"""
    
    @staticmethod
    def aggregate(results: List[EvaluationResult]) -> Dict[str, float]:
        """Compute average metrics across all episodes"""
        if not results:
            return {}
        
        # Filter out errors
        valid_results = [r for r in results if r.error_message is None]
        if not valid_results:
            logger.warning("No valid results to aggregate")
            return {}
        
        aggregated = {}
        metrics = [
            "success", "spl", "path_length", "oracle_success", "oracle_spl",
            "ndtw", "sdtw", "steps", "collisions", "tcr", "cr", "sr_human"
        ]
        
        for metric in metrics:
            values = [getattr(r, metric) for r in valid_results]
            aggregated[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
                "count": len(values)
            }
        
        return aggregated


# ============================================================================
# Stage 5: Reporter
# ============================================================================

class ResultReporter:
    """Generates leaderboard and per-episode reports"""
    
    @staticmethod
    def generate_leaderboard(aggregated: Dict[str, float]) -> Dict[str, Any]:
        """Generate public leaderboard metrics"""
        return {
            "sr_human": aggregated.get("sr_human", {}).get("mean", 0.0),
            "spl": aggregated.get("spl", {}).get("mean", 0.0),
            "ndtw": aggregated.get("ndtw", {}).get("mean", 0.0),
            "sdtw": aggregated.get("sdtw", {}).get("mean", 0.0),
            "collisions": aggregated.get("collisions", {}).get("mean", 0.0),
            "tcr": aggregated.get("tcr", {}).get("mean", 0.0),
        }
    
    @staticmethod
    def save_results(
        leaderboard: Dict[str, Any],
        per_episode: List[Dict[str, Any]],
        aggregated: Dict[str, float],
        output_path: str
    ):
        """Save all results to files"""
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Leaderboard
        leaderboard_path = output_dir / "leaderboard.json"
        with open(leaderboard_path, 'w') as f:
            json.dump(leaderboard, f, indent=2)
        logger.info(f"Saved leaderboard to {leaderboard_path}")
        
        # Per-episode details
        per_episode_path = output_dir / "per_episode.json"
        with open(per_episode_path, 'w') as f:
            json.dump(per_episode, f, indent=2)
        logger.info(f"Saved per-episode results to {per_episode_path}")
        
        # Aggregated statistics
        aggregated_path = output_dir / "aggregated.json"
        with open(aggregated_path, 'w') as f:
            json.dump(aggregated, f, indent=2)
        logger.info(f"Saved aggregated stats to {aggregated_path}")
        
        # Summary
        summary_path = output_dir / "summary.txt"
        with open(summary_path, 'w') as f:
            f.write("=== HA-VLN Challenge Evaluation Summary ===\n\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Episodes evaluated: {len(per_episode)}\n\n")
            f.write("Public Leaderboard Metrics:\n")
            for key, value in sorted(leaderboard.items()):
                f.write(f"  {key:20s}: {value:.6f}\n")
        logger.info(f"Saved summary to {summary_path}")


# ============================================================================
# Main Evaluation Pipeline
# ============================================================================

def load_submission(submission_path: str) -> Dict[str, Any]:
    """Load submission JSON"""
    with open(submission_path, 'r') as f:
        return json.load(f)


def load_test_split(test_path: str) -> set:
    """Load test split and extract valid episode IDs"""
    with gzip.open(test_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    
    episode_ids = set()
    for ep in data.get("episodes", []):
        episode_ids.add(str(ep.get("episode_id")))
    
    return episode_ids


def run_evaluation(
    submission_path: str,
    config_path: str,
    output_dir: str = "./eval_results"
):
    """Run full evaluation pipeline"""
    
    logger.info("=" * 80)
    logger.info("HA-VLN Challenge Evaluator - Starting")
    logger.info("=" * 80)
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)
    logger.info(f"Loaded config from {config_path}")
    
    # Load submission
    logger.info(f"\n--- Stage 1: Submission Validator ---")
    submission = load_submission(submission_path)
    logger.info(f"Loaded submission from {submission_path}")
    
    test_episode_ids = load_test_split(config["test_path"])
    logger.info(f"Loaded {len(test_episode_ids)} test episodes")
    
    validator = SubmissionValidator(test_episode_ids)
    is_valid, validation_msgs = validator.validate(submission)
    
    for msg in validation_msgs:
        logger.info(msg)
    
    if not is_valid:
        logger.error("Submission validation failed!")
        return
    
    logger.info("✓ Submission validation passed")
    
    # Evaluate episodes
    logger.info(f"\n--- Stage 2-3: Replay & Metric Engine ---")
    evaluator = ChallengeEvaluator(config)
    
    results = []
    episodes = submission.get("episodes", [])
    for i, ep_data in enumerate(episodes):
        ep_id = str(ep_data["episode_id"])
        actions = ep_data["actions"]
        
        if (i + 1) % max(1, len(episodes) // 10) == 0:
            logger.info(f"Evaluated {i + 1}/{len(episodes)} episodes")
        
        result = evaluator.evaluate(ep_id, actions)
        results.append(result)
    
    logger.info(f"✓ Evaluated {len(results)} episodes")
    
    # Aggregate results
    logger.info(f"\n--- Stage 4: Aggregator ---")
    aggregated = ResultAggregator.aggregate(results)
    logger.info("✓ Aggregated results")
    
    # Generate reports
    logger.info(f"\n--- Stage 5: Reporter ---")
    leaderboard = ResultReporter.generate_leaderboard(aggregated)
    
    per_episode_dicts = [r.to_dict() for r in results]
    
    ResultReporter.save_results(
        leaderboard,
        per_episode_dicts,
        aggregated,
        output_dir
    )
    
    logger.info("=" * 80)
    logger.info("Evaluation Complete")
    logger.info("=" * 80)
    logger.info("\nPublic Leaderboard Results:")
    for key, value in sorted(leaderboard.items()):
        logger.info(f"  {key:20s}: {value:.6f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HA-VLN Challenge Evaluator"
    )
    parser.add_argument(
        "submission",
        help="Path to submission JSON file"
    )
    parser.add_argument(
        "--config",
        default="challenge/config.json",
        help="Path to evaluator config (default: challenge/config.json)"
    )
    parser.add_argument(
        "--output",
        default="./eval_results",
        help="Output directory for results (default: ./eval_results)"
    )
    
    args = parser.parse_args()
    
    run_evaluation(args.submission, args.config, args.output)
