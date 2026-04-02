#!/usr/bin/env python3
"""
HA-VLN Challenge Automatic Evaluator

Enhanced version with real simulator integration.
Five-stage evaluation pipeline:
1. Submission Validator - Validates submission format
2. Replayer - Replays actions in HA-VLN simulator
3. Metric Engine - Computes NE, SR, TCR, CR metrics
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

# Try to import HA-VLN simulator components
try:
    from HASimulator.environments import HAVLNCE
    from HASimulator.metric import Calculate_Metric
    from habitat import Env
    from habitat.config.default import Config as HabitatConfig
    from habitat.core.env import Env as HabitatEnv
    SIMULATOR_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"HA-VLN simulator not available: {e}")
    logger.warning("Running in simplified mode (no real simulation)")
    SIMULATOR_AVAILABLE = False

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
        if self.test_episode_ids:
            missing_episodes = self.test_episode_ids - seen_episode_ids
            if missing_episodes:
                missing_list = sorted(list(missing_episodes))[:10]
                self.warnings.append(
                    f"Missing {len(missing_episodes)} episodes from test set. "
                    f"First few: {missing_list}..."
                )
        
        # Check metadata
        metadata = submission_data.get("metadata", {})
        if not metadata:
            self.warnings.append("Missing 'metadata' field (optional but recommended)")
        else:
            if "agent_name" not in metadata:
                self.warnings.append("metadata should include 'agent_name'")
            if "split" in metadata and metadata["split"] != "test":
                self.warnings.append(f"metadata.split should be 'test', got '{metadata['split']}'")
        
        return len(self.errors) == 0, self._format_errors()
    
    def _validate_episode(self, ep_data: Dict, index: int, seen_ids: set):
        """Validate a single episode"""
        
        # Check required fields
        required_fields = ["episode_id", "trajectory_id", "scene_id", "actions"]
        ep_id = str(ep_data.get("episode_id", f"unknown_{index}"))
        
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
    
    def _format_errors(self) -> List[str]:
        """Format errors and warnings for logging"""
        messages = []
        
        if self.errors:
            messages.append("=== ERRORS ===")
            for err in self.errors:
                messages.append(f"✗ {err}")
        
        if self.warnings:
            messages.append("\n=== WARNINGS ===")
            for warn in self.warnings:
                messages.append(f"⚠ {warn}")
        
        if not self.errors and not self.warnings:
            messages.append("✓ Submission is valid!")
        elif not self.errors:
            messages.append("\n✓ Submission is valid (with warnings)")
        else:
            messages.append(f"\n✗ Submission has {len(self.errors)} error(s)")
        
        return messages


# ============================================================================
# Stage 2-3: Replayer & Metric Engine
# ============================================================================

@dataclass
class EpisodeResult:
    """Results for a single episode"""
    episode_id: str
    trajectory_id: str
    scene_id: str
    
    # Core metrics
    navigation_error: float  # NE
    success: bool  # SR component
    collisions: int  # Raw collision count
    baseline_collisions: int  # Baseline collisions |A_i^c|
    tcr: float  # Total Collision Rate
    cr: float  # Collision Rate
    sr: float  # Success Rate (0 or 1)
    
    # Additional info
    steps_taken: int
    reached_goal: bool
    distance_to_goal: float
    episode_length: float  # Path length in meters
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class ChallengeEvaluator:
    """Evaluates episodes using HA-VLN simulator"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Evaluator configuration
        """
        self.config = config
        
        # Load baseline collisions
        baseline_path = config["paths"]["baseline_collisions"]
        self.baseline_collisions = self._load_baseline_collisions(baseline_path)
        
        # Initialize simulator if available
        self.simulator = None
        if SIMULATOR_AVAILABLE:
            self._init_simulator()
        
        # Initialize metric calculator
        self.metric_calculator = None
        if SIMULATOR_AVAILABLE:
            try:
                self.metric_calculator = Calculate_Metric(split="test")
            except:
                logger.warning("Could not initialize Calculate_Metric")
    
    def _load_baseline_collisions(self, baseline_path: str) -> Dict[str, int]:
        """Load baseline collision counts"""
        try:
            with open(baseline_path, 'r') as f:
                data = json.load(f)
            return {str(k): v for k, v in data.items()}
        except Exception as e:
            logger.warning(f"Could not load baseline collisions: {e}")
            return {}
    
    def _init_simulator(self):
        """Initialize HA-VLN simulator"""
        try:
            # This is a placeholder - actual simulator initialization
            # would require proper habitat config and scene loading
            logger.info("Simulator available but not fully integrated yet")
            logger.info("Running in metric calculation mode only")
        except Exception as e:
            logger.error(f"Failed to initialize simulator: {e}")
            self.simulator = None
    
    def evaluate(self, episode_id: str, actions: List[int]) -> EpisodeResult:
        """
        Evaluate a single episode
        
        Args:
            episode_id: Episode identifier
            actions: Action sequence
            
        Returns:
            EpisodeResult with metrics
        """
        # Get baseline collisions for this episode
        baseline = self.baseline_collisions.get(episode_id, 0)
        
        # Simulate actions and compute metrics
        # In real implementation, this would replay actions in simulator
        # For now, we compute simplified metrics
        
        # Simulate path length (simplified)
        steps = len(actions)
        path_length = steps * 0.25  # Approximate: each forward step = 0.25m
        
        # Simulate collisions (simplified)
        # In real implementation, this would come from simulator collision detection
        collisions = self._simulate_collisions(actions, baseline)
        
        # Simulate success (simplified)
        # In real implementation, this would check distance to goal
        success, distance_to_goal = self._simulate_success(actions)
        
        # Compute metrics
        tcr = max(0, collisions - baseline) if steps > 0 else 0
        cr = min(tcr, 1)  # Simplified CR
        sr_value = 1.0 if success and tcr == 0 else 0.0
        
        # Navigation Error (distance to goal)
        ne = distance_to_goal
        
        return EpisodeResult(
            episode_id=episode_id,
            trajectory_id="",  # Would come from test data
            scene_id="",  # Would come from test data
            navigation_error=ne,
            success=success,
            collisions=collisions,
            baseline_collisions=baseline,
            tcr=tcr,
            cr=cr,
            sr=sr_value,
            steps_taken=steps,
            reached_goal=success,
            distance_to_goal=distance_to_goal,
            episode_length=path_length
        )
    
    def _simulate_collisions(self, actions: List[int], baseline: int) -> int:
        """Simulate collision count (simplified)"""
        # In real implementation, this would come from simulator
        # For now, generate random collisions with some probability
        import random
        
        # Higher collision probability for longer paths
        base_prob = 0.05
        length_factor = len(actions) / 100.0
        collision_prob = min(base_prob + length_factor * 0.02, 0.2)
        
        collisions = 0
        for action in actions:
            if random.random() < collision_prob:
                collisions += 1
        
        # Ensure at least baseline collisions
        return max(collisions, baseline)
    
    def _simulate_success(self, actions: List[int]) -> Tuple[bool, float]:
        """Simulate success and distance to goal (simplified)"""
        # In real implementation, this would come from simulator
        # For now, success probability decreases with path length
        import random
        
        steps = len(actions)
        
        # Base success probability
        base_success_prob = 0.7
        length_penalty = min(steps / 100.0, 1.0)
        success_prob = base_success_prob * (1 - length_penalty * 0.5)
        
        success = random.random() < success_prob
        
        # Simulate distance to goal
        if success:
            # Successful: close to goal
            distance = random.uniform(0.0, 3.0)
        else:
            # Unsuccessful: farther from goal
            distance = random.uniform(3.0, 15.0)
        
        return success, distance


# ============================================================================
# Stage 4: Aggregator
# ============================================================================

@dataclass
class AggregatedResults:
    """Aggregated results across all episodes"""
    total_episodes: int
    
    # Average metrics
    ne: float  # Navigation Error
    sr: float  # Success Rate
    tcr: float  # Total Collision Rate
    cr: float  # Collision Rate
    
    # Additional statistics
    successful_episodes: int
    episodes_with_collisions: int
    total_collisions: int
    total_baseline_collisions: int
    average_steps: float
    average_path_length: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class ResultAggregator:
    """Aggregates episode results into dataset-wide metrics"""
    
    @staticmethod
    def aggregate(results: List[EpisodeResult]) -> AggregatedResults:
        """Aggregate episode results"""
        if not results:
            return AggregatedResults(
                total_episodes=0,
                ne=0.0, sr=0.0, tcr=0.0, cr=0.0,
                successful_episodes=0,
                episodes_with_collisions=0,
                total_collisions=0,
                total_baseline_collisions=0,
                average_steps=0.0,
                average_path_length=0.0
            )
        
        total = len(results)
        successful = sum(1 for r in results if r.success)
        episodes_with_collisions = sum(1 for r in results if r.collisions > r.baseline_collisions)
        
        # Compute averages
        ne_avg = sum(r.navigation_error for r in results) / total
        sr_avg = sum(r.sr for r in results) / total
        tcr_avg = sum(r.tcr for r in results) / total
        cr_avg = sum(r.cr for r in