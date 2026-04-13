#!/usr/bin/env python3

import argparse
import copy
import importlib
import json
import os
import sys
from typing import Any, Dict, List, Tuple

import torch
from habitat import logger
from habitat_baselines.common.baseline_registry import baseline_registry


AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
VLN_CE_DIR = os.path.join(AGENT_DIR, "VLN-CE")
REPO_ROOT = os.path.dirname(AGENT_DIR)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)
if VLN_CE_DIR not in sys.path:
    sys.path.insert(0, VLN_CE_DIR)

import habitat_extensions  # noqa: F401
import vlnce_baselines  # noqa: F401
from HASimulator.metric import Calculate_Metric
from eval_utils import (
    OFFLINE_EVAL_INPUT_FILENAME,
    aggregate_episode_metrics,
    write_eval_outputs,
)
from vlnce_baselines.common.environments import HAVLNCEDaggerEnv


DEFAULT_FACTORY_FN = "build_agent"
DEFAULT_ACTIONS = ["STOP", "MOVE_FORWARD", "TURN_LEFT", "TURN_RIGHT"]


def evaluate_submission(config) -> Dict[str, float]:
    eval_config = _build_eval_config(config)
    os.makedirs(eval_config.RESULTS_DIR, exist_ok=True)

    env_class = baseline_registry.get_env("HAVLNCEDaggerEnv")
    assert env_class is HAVLNCEDaggerEnv, "Failed to resolve HAVLNCEDaggerEnv."
    env = env_class(config=eval_config)

    runtime_spec = _build_runtime_spec(eval_config, env)
    agent = _build_agent(eval_config, runtime_spec)

    split = eval_config.TASK_CONFIG.DATASET.SPLIT
    score_adjuster = Calculate_Metric(split=split)

    score_rows: List[Dict[str, Any]] = []
    aux_rows: Dict[str, Dict[str, Any]] = {}
    stats_episodes: Dict[str, Dict[str, Any]] = {}
    raw_stats_episodes: Dict[str, Dict[str, Any]] = {}
    episode_contexts: Dict[str, Dict[str, Any]] = {}
    action_traces: Dict[str, List[str]] = {}

    try:
        total_episodes = len(env.episodes)
        if eval_config.EVAL.EPISODE_COUNT > -1:
            total_episodes = min(eval_config.EVAL.EPISODE_COUNT, total_episodes)

        for idx in range(total_episodes):
            logger.info(f"[debug] about to reset env for episode_index={idx}")
            observations = env.reset()
            logger.info(f"[debug] env.reset finished for episode_index={idx}")
            episode = env.current_episode
            logger.info(f"[debug] current_episode_id={episode.episode_id}")
            episode_context = _build_episode_context(episode)
            ep_id = str(episode.episode_id)
            episode_contexts[ep_id] = copy.deepcopy(episode_context)
            agent.reset(episode_context)

            done = False
            info: Dict[str, Any] = {}
            action_trace: List[str] = []
            while not done:
                action_name = agent.act(copy.deepcopy(observations))
                assert (
                    action_name in eval_config.TASK_CONFIG.TASK.POSSIBLE_ACTIONS
                ), (
                    "Agent returned unsupported action "
                    f"{action_name!r}. Allowed actions: "
                    f"{list(eval_config.TASK_CONFIG.TASK.POSSIBLE_ACTIONS)}"
                )
                action_trace.append(action_name)
                observations, _, done, info = env.step(action_name)

            action_traces[ep_id] = action_trace
            raw_stats_episodes[ep_id] = copy.deepcopy(info)
            episode_metrics = copy.deepcopy(info)
            score_adjuster(episode_metrics, ep_id)
            stats_episodes[ep_id] = episode_metrics
            score_rows.append(_build_episode_metrics_row(split, ep_id, episode_metrics))
            aux_row = _extract_aux_metrics(info)
            if aux_row:
                aux_rows[ep_id] = aux_row
    finally:
        try:
            agent.close()
        finally:
            env.close()

    aggregated_stats = aggregate_episode_metrics(stats_episodes)
    write_eval_outputs(eval_config, split, aggregated_stats, score_rows, aux_rows)
    _write_offline_eval_input(
        eval_config,
        split,
        aggregated_stats,
        score_rows,
        aux_rows,
        raw_stats_episodes,
        stats_episodes,
        episode_contexts,
        action_traces,
    )
    logger.info(f"Episodes evaluated: {len(stats_episodes)}")
    for key, value in aggregated_stats.items():
        logger.info(f"{key}: {value:.6f}")
    return aggregated_stats


def _build_eval_config(config):
    eval_config = config.clone()
    eval_config.defrost()
    eval_config.ENV_NAME = "HAVLNCEDaggerEnv"
    eval_config.NUM_ENVIRONMENTS = 1
    eval_config.TASK_CONFIG.DATASET.SPLIT = config.EVAL.SPLIT
    eval_config.TASK_CONFIG.DATASET.ROLES = ["guide"]
    eval_config.TASK_CONFIG.DATASET.LANGUAGES = config.EVAL.LANGUAGES
    eval_config.TASK_CONFIG.TASK.NDTW.SPLIT = config.EVAL.SPLIT
    eval_config.TASK_CONFIG.ENVIRONMENT.ITERATOR_OPTIONS.SHUFFLE = False
    eval_config.TASK_CONFIG.ENVIRONMENT.ITERATOR_OPTIONS.MAX_SCENE_REPEAT_STEPS = -1
    eval_config.TASK_CONFIG.TASK.POSSIBLE_ACTIONS = DEFAULT_ACTIONS
    eval_config.freeze()
    return eval_config


def _build_runtime_spec(config, env) -> Dict[str, Any]:
    policy_config = config.clone()
    policy_config.defrost()
    policy_config.TRAINER_NAME = ""
    policy_config.ENV_NAME = ""
    policy_config.freeze()
    return {
        "device": (
            torch.device("cuda", config.TORCH_GPU_ID)
            if torch.cuda.is_available()
            else torch.device("cpu")
        ),
        "observation_space": env.observation_space,
        "action_space": env.action_space,
        "policy_config": policy_config,
        "instruction_sensor_uuid": config.TASK_CONFIG.TASK.INSTRUCTION_SENSOR_UUID,
        "allowed_actions": list(config.TASK_CONFIG.TASK.POSSIBLE_ACTIONS),
    }


def _build_agent(config, runtime_spec):
    adapter_cfg = config.CHALLENGE_AGENT
    module_name = adapter_cfg.MODULE
    assert module_name, "CHALLENGE_AGENT.MODULE must be set in the submission config."
    factory_name = adapter_cfg.FACTORY_FN or DEFAULT_FACTORY_FN
    adapter_module = importlib.import_module(module_name)
    assert hasattr(
        adapter_module, factory_name
    ), f"Adapter module {module_name!r} does not expose factory {factory_name!r}."
    build_fn = getattr(adapter_module, factory_name)
    agent = build_fn(_cfg_node_to_dict(adapter_cfg.CONFIG), runtime_spec)
    for method_name in ["reset", "act", "close"]:
        assert hasattr(agent, method_name), (
            f"Challenge agent from {module_name!r} is missing required method "
            f"{method_name!r}."
        )
    return agent


def _build_config_snapshot(config, split: str) -> Dict[str, Any]:
    return {
        "BASE_TASK_CONFIG_PATH": config.BASE_TASK_CONFIG_PATH,
        "TORCH_GPU_ID": config.TORCH_GPU_ID,
        "RESULTS_DIR": config.RESULTS_DIR,
        "LOG_FILE": config.LOG_FILE,
        "EVAL": {
            "SPLIT": split,
            "EPISODE_COUNT": config.EVAL.EPISODE_COUNT,
            "LANGUAGES": list(config.EVAL.LANGUAGES),
        },
        "CHALLENGE_AGENT": {
            "MODULE": config.CHALLENGE_AGENT.MODULE,
            "FACTORY_FN": config.CHALLENGE_AGENT.FACTORY_FN,
            "CONFIG": _cfg_node_to_dict(config.CHALLENGE_AGENT.CONFIG),
        },
        "TASK_CONFIG": {
            "DATASET": {
                "SPLIT": config.TASK_CONFIG.DATASET.SPLIT,
                "ROLES": list(config.TASK_CONFIG.DATASET.ROLES),
                "LANGUAGES": list(config.TASK_CONFIG.DATASET.LANGUAGES),
            },
            "TASK": {
                "POSSIBLE_ACTIONS": list(config.TASK_CONFIG.TASK.POSSIBLE_ACTIONS),
                "INSTRUCTION_SENSOR_UUID": config.TASK_CONFIG.TASK.INSTRUCTION_SENSOR_UUID,
            },
        },
    }


def _cfg_node_to_dict(node):
    if hasattr(node, "items"):
        return {key: _cfg_node_to_dict(value) for key, value in node.items()}
    if isinstance(node, (list, tuple)):
        return [_cfg_node_to_dict(value) for value in node]
    return node


def _build_episode_context(episode) -> Dict[str, Any]:
    instruction = getattr(episode, "instruction", None)
    return {
        "episode_id": str(episode.episode_id),
        "scene_id": episode.scene_id,
        "trajectory_id": getattr(episode, "trajectory_id", None),
        "instruction": getattr(instruction, "instruction_text", None),
    }


def _extract_aux_metrics(info: Dict[str, Any]) -> Dict[str, Any]:
    aux_metrics = {}
    for key in ["distance_to_human", "collisions_detail", "human_counting"]:
        if key in info:
            aux_metrics[key] = copy.deepcopy(info[key])
    return aux_metrics


def _build_episode_metrics_row(
    split: str, episode_id: str, episode_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    collision_count = episode_metrics["collisions"]["count"]
    adjusted_collision_count = episode_metrics["TCR"]
    return {
        "episode_id": episode_id,
        "split": split,
        "success": episode_metrics["success"],
        "goal_distance": episode_metrics["distance_to_goal"],
        "collision_count": collision_count,
        "baseline_collision_count": max(0, collision_count - adjusted_collision_count),
        "adjusted_collision_count": adjusted_collision_count,
        "collision_indicator": episode_metrics["CR"],
        "strict_success": episode_metrics["SR"],
    }


def _write_offline_eval_input(
    config,
    split: str,
    aggregated_stats: Dict[str, float],
    episode_rows: List[Dict[str, Any]],
    aux_rows: Dict[str, Dict[str, Any]],
    raw_stats_episodes: Dict[str, Dict[str, Any]],
    adjusted_stats_episodes: Dict[str, Dict[str, Any]],
    episode_contexts: Dict[str, Dict[str, Any]],
    action_traces: Dict[str, List[str]],
) -> None:
    artifact = {
        "format_version": 1,
        "split": split,
        "config_snapshot": _build_config_snapshot(config, split),
        "aggregated_stats": copy.deepcopy(aggregated_stats),
        "episode_rows": copy.deepcopy(episode_rows),
        "aux_rows": copy.deepcopy(aux_rows),
        "raw_stats_episodes": copy.deepcopy(raw_stats_episodes),
        "adjusted_stats_episodes": copy.deepcopy(adjusted_stats_episodes),
        "episode_contexts": copy.deepcopy(episode_contexts),
        "action_traces": copy.deepcopy(action_traces),
    }
    offline_input_path = os.path.join(config.RESULTS_DIR, OFFLINE_EVAL_INPUT_FILENAME)
    with open(offline_input_path, "w", encoding="utf-8") as handle:
        json.dump(artifact, handle, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--exp-config",
        type=str,
        required=True,
        help="path to config yaml containing info about experiment",
    )
    parser.add_argument(
        "opts",
        default=None,
        nargs=argparse.REMAINDER,
        help="Modify config options from command line",
    )

    args = parser.parse_args()
    try:
        from vlnce_baselines.config.default import get_config

        config = get_config(args.exp_config, args.opts)
        logdir = "/".join(config.LOG_FILE.split("/")[:-1])
        if logdir:
            os.makedirs(logdir, exist_ok=True)
        logger.add_filehandler(config.LOG_FILE)
        evaluate_submission(config)
    except (
        AssertionError,
        FileNotFoundError,
        ImportError,
        ModuleNotFoundError,
        ValueError,
    ) as exc:
        raise SystemExit(f"Challenge evaluation failed: {exc}") from None


if __name__ == "__main__":
    main()
