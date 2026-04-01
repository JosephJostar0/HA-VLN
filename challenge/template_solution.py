#!/usr/bin/env python3
"""
HA-VLN Challenge - Solution Template

This is a starting template for developing solutions.
Implement your own navigation model and generate actions for all test episodes.
"""

import json
import gzip
import random
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NavigationModel:
    """Base class for navigation models"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
    
    def predict(
        self,
        episode: Dict[str, Any],
        max_steps: int = 500
    ) -> List[int]:
        """
        Predict action sequence for episode
        
        Args:
            episode: Episode dict with instruction, start_position, etc.
            max_steps: Maximum steps before auto-STOP
        
        Returns:
            List of action codes [0-3]
        """
        raise NotImplementedError


class RandomPolicy(NavigationModel):
    """Baseline: Random action sampler"""
    
    def predict(self, episode: Dict[str, Any], max_steps: int = 500) -> List[int]:
        """Randomly sample actions until STOP"""
        num_steps = random.randint(1, min(max_steps - 1, 50))
        actions = [random.randint(1, 3) for _ in range(num_steps)]
        actions.append(0)  # STOP
        return actions


class ForwardWalkPolicy(NavigationModel):
    """Baseline: Always move forward"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.forward_steps = config.get("forward_steps", 20) if config else 20
    
    def predict(self, episode: Dict[str, Any], max_steps: int = 500) -> List[int]:
        """Walk forward for N steps then stop"""
        actions = [1] * self.forward_steps + [0]  # MOVE_FORWARD * N + STOP
        return actions


class SmartWalkPolicy(NavigationModel):
    """Slightly smarter baseline: Alternate directions"""
    
    def predict(self, episode: Dict[str, Any], max_steps: int = 500) -> List[int]:
        """Walk forward, occasionally turn"""
        actions = []
        for i in range(30):
            if i % 5 == 0 and i > 0:
                actions.append(random.choice([2, 3]))  # Turn occasionally
            else:
                actions.append(1)  # Move forward
        actions.append(0)  # Stop
        return actions


class HabitatPolicy(NavigationModel):
    """
    Integration point for Habitat-based models
    
    Example with actual Habitat:
    
    from habitat import Env
    from habitat.core.logging import logger
    
    class HabitatPolicy(NavigationPolicy):
        def __init__(self, config_path: str):
            self.env = Env(config=habitat.get_config(config_path))
        
        def predict(self, episode: Dict, max_steps: int = 500) -> List[int]:
            obs = self.env.reset()
            actions = []
            for step in range(max_steps):
                # Use observation to predict action
                action = self.forward_pass(obs)
                actions.append(action)
                
                if action == 0:  # STOP
                    break
                
                obs = self.env.step(action)
            
            return actions
    """
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config_path = config_path
        # TODO: Initialize Habitat environment if config provided
    
    def predict(self, episode: Dict[str, Any], max_steps: int = 500) -> List[int]:
        """Placeholder for Habitat-based model"""
        # TODO: Implement actual Habitat forward pass
        
        # For now, return forward walk
        return [1] * 20 + [0]
    
    def forward_pass(self, obs):
        """Model inference on observation"""
        # TODO: Implement your model forward pass
        # Examples:
        #   - vision_transformer(obs)
        #   - bert_lstm(instruction, visual_features)
        #   - graph_neural_network(scene_graph)
        raise NotImplementedError


class SolutionGenerator:
    """Generates complete submission for all test episodes"""
    
    def __init__(self, model: NavigationModel):
        self.model = model
    
    def generate_submission(
        self,
        test_episodes: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate submission for all test episodes
        
        Args:
            test_episodes: List of episodes from test split
            metadata: Optional team/model metadata
        
        Returns:
            Submission dict ready for evaluation
        """
        episodes = []
        
        for i, test_ep in enumerate(test_episodes):
            if (i + 1) % 500 == 0:
                logger.info(f"Processed {i + 1}/{len(test_episodes)} episodes")
            
            # Get action sequence
            actions = self.model.predict(test_ep)
            
            # Validate actions
            self._validate_actions(actions)
            
            # Build submission episode
            submission_ep = {
                "episode_id": str(test_ep["episode_id"]),
                "trajectory_id": test_ep.get("trajectory_id", ""),
                "scene_id": test_ep.get("scene_id", ""),
                "actions": actions
            }
            
            episodes.append(submission_ep)
        
        # Build submission
        submission = {
            "metadata": metadata or self._default_metadata(),
            "episodes": episodes
        }
        
        return submission
    
    def _validate_actions(self, actions: List[int]):
        """Validate action sequence"""
        if not actions:
            raise ValueError("Action sequence cannot be empty")
        
        if len(actions) > 500:
            raise ValueError(f"Too many actions: {len(actions)} > 500")
        
        for i, action in enumerate(actions):
            if not isinstance(action, int):
                raise TypeError(f"Action {i} is {type(action)}, not int")
            
            if action not in [0, 1, 2, 3]:
                raise ValueError(f"Action {i} = {action}, must be in [0, 1, 2, 3]")
        
        if actions[-1] != 0:
            raise ValueError("Last action must be STOP (0)")
    
    def _default_metadata(self) -> Dict[str, Any]:
        """Default metadata"""
        return {
            "team_name": "Anonymous",
            "model": self.__class__.__name__,
            "description": "Submission from HA-VLN starter kit"
        }


def load_test_split(test_path: str) -> List[Dict[str, Any]]:
    """Load test split from gzip JSON"""
    logger.info(f"Loading test split from {test_path}")
    with gzip.open(test_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    
    episodes = data.get("episodes", [])
    logger.info(f"Loaded {len(episodes)} test episodes")
    return episodes


def save_submission(submission: Dict[str, Any], output_path: str):
    """Save submission to JSON file"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(submission, f, indent=2)
    
    logger.info(f"Saved submission to {output_path}")
    logger.info(f"Episodes: {len(submission['episodes'])}")


def main():
    parser = argparse.ArgumentParser(
        description="HA-VLN Challenge - Solution Template"
    )
    
    parser.add_argument(
        "--test-path",
        default="Data/HA-R2R/test.json.gz",
        help="Path to test split (default: Data/HA-R2R/test.json.gz)"
    )
    
    parser.add_argument(
        "--output",
        default="submission.json",
        help="Output submission file (default: submission.json)"
    )
    
    parser.add_argument(
        "--policy",
        default="forward",
        choices=["random", "forward", "smart"],
        help="Policy to use (default: forward)"
    )
    
    parser.add_argument(
        "--team-name",
        default="Anonymous",
        help="Team name for submission"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    
    args = parser.parse_args()
    
    # Set seed if provided
    if args.seed is not None:
        random.seed(args.seed)
        logger.info(f"Set random seed to {args.seed}")
    
    # Load test split
    test_episodes = load_test_split(args.test_path)
    
    # Create model
    if args.policy == "random":
        model = RandomPolicy()
    elif args.policy == "smart":
        model = SmartWalkPolicy()
    else:  # forward
        model = ForwardWalkPolicy()
    
    logger.info(f"Using policy: {args.policy}")
    
    # Generate submission
    generator = SolutionGenerator(model)
    submission = generator.generate_submission(
        test_episodes,
        metadata={
            "team_name": args.team_name,
            "model": args.policy,
            "description": f"{args.policy} walk policy"
        }
    )
    
    # Save
    save_submission(submission, args.output)


if __name__ == "__main__":
    main()
