import copy
import json
import os
from typing import Any, Dict, List


OFFLINE_EVAL_INPUT_FILENAME = "offline_eval_input.json"


def aggregate_episode_metrics(
    stats_episodes: Dict[str, Dict[str, Any]]
) -> Dict[str, float]:
    assert stats_episodes, "No episodes were evaluated."
    aggregated_stats: Dict[str, float] = {}
    stats_episodes = copy.deepcopy(stats_episodes)
    num_episodes = len(stats_episodes)

    for episode_metrics in stats_episodes.values():
        if "distance_to_human" in episode_metrics:
            del episode_metrics["distance_to_human"]
        if "collisions_detail" in episode_metrics:
            del episode_metrics["collisions_detail"]

    for key in next(iter(stats_episodes.values())).keys():
        if key == "collisions":
            aggregated_stats[key] = (
                sum(metrics[key]["count"] for metrics in stats_episodes.values())
                / num_episodes
            )
        else:
            aggregated_stats[key] = (
                sum(metrics[key] for metrics in stats_episodes.values()) / num_episodes
            )

    return aggregated_stats


def write_eval_outputs(
    config,
    split: str,
    aggregated_stats: Dict[str, float],
    episode_rows: List[Dict[str, Any]],
    aux_rows: Dict[str, Dict[str, Any]],
) -> None:
    summary_path = os.path.join(config.RESULTS_DIR, f"stats_ckpt_0_{split}.json")
    with open(summary_path, "w", encoding="utf-8") as handle:
        json.dump(aggregated_stats, handle, indent=4)

    if aux_rows:
        aux_path = os.path.join(config.RESULTS_DIR, f"stats_ckpt_0_{split}_info.json")
        with open(aux_path, "w", encoding="utf-8") as handle:
            json.dump(aux_rows, handle, indent=4)

    episode_metrics_path = os.path.join(config.RESULTS_DIR, "episode_metrics.json")
    with open(episode_metrics_path, "w", encoding="utf-8") as handle:
        json.dump(episode_rows, handle, indent=2)

    score_summary = {
        "split": split,
        "num_episodes": len(episode_rows),
        "SR": aggregated_stats.get("SR"),
        "TCR": aggregated_stats.get("TCR"),
        "CR": aggregated_stats.get("CR"),
        "NE": aggregated_stats.get("distance_to_goal"),
    }
    score_summary_path = os.path.join(config.RESULTS_DIR, "score_summary.json")
    with open(score_summary_path, "w", encoding="utf-8") as handle:
        json.dump(score_summary, handle, indent=2)
