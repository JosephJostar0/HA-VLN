#!/usr/bin/env bash

set -euo pipefail

AGENT_ROOT="/app/agent"
CONFIG_PATH="${AGENT_ROOT}/config/challenge_submission.yaml"

cd "${AGENT_ROOT}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Submission config not found: ${CONFIG_PATH}" >&2
  exit 1
fi

RESULT_OPTS=()
if [[ -d "/app/result" ]]; then
  RESULT_OPTS+=("RESULTS_DIR" "/app/result")
  RESULT_OPTS+=("LOG_FILE" "/app/result/challenge_eval.log")
fi

python "${AGENT_ROOT}/run.py" \
  --run-type eval \
  --exp-config "${CONFIG_PATH}" \
  "${RESULT_OPTS[@]}"
