#!/usr/bin/env python3

import argparse
import json
import os
from types import SimpleNamespace

from eval_utils import (
    OFFLINE_EVAL_INPUT_FILENAME,
    aggregate_episode_metrics,
    write_eval_outputs,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input-path",
        type=str,
        default=None,
        help=(
            "path to the offline evaluator artifact exported by eval.py; "
            f"defaults to {OFFLINE_EVAL_INPUT_FILENAME} under --results-dir"
        ),
    )
    parser.add_argument(
        "--results-dir",
        type=str,
        default=".",
        help=(
            "directory used to locate offline_eval_input.json when --input-path "
            "is not provided"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=(
            "directory where the recreated evaluation outputs will be written; "
            "defaults to --results-dir"
        ),
    )
    args = parser.parse_args()

    input_path = args.input_path or os.path.join(
        args.results_dir, OFFLINE_EVAL_INPUT_FILENAME
    )
    output_dir = args.output_dir or args.results_dir
    with open(input_path, "r", encoding="utf-8") as handle:
        artifact = json.load(handle)

    assert artifact.get("format_version") == 1, "Unsupported offline eval artifact."
    split = artifact["split"]
    adjusted_stats_episodes = artifact["adjusted_stats_episodes"]
    episode_rows = artifact["episode_rows"]
    aux_rows = artifact.get("aux_rows", {})

    aggregated_stats = aggregate_episode_metrics(adjusted_stats_episodes)
    output_config = SimpleNamespace(RESULTS_DIR=output_dir)
    os.makedirs(output_dir, exist_ok=True)
    write_eval_outputs(output_config, split, aggregated_stats, episode_rows, aux_rows)


if __name__ == "__main__":
    main()
