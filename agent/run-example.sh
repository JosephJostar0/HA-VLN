#!/usr/bin/env bash

set -eo pipefail

AGENT_ROOT="/app/agent"
CONFIG_PATH="${AGENT_ROOT}/config/challenge_submission.yaml"

source /opt/conda/etc/profile.d/conda.sh
conda activate havlnce
set -u

cd "${AGENT_ROOT}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "Submission config not found: ${CONFIG_PATH}" >&2
  exit 1
fi

mkdir -p /app/result

python "${AGENT_ROOT}/run.py" \
  --run-type eval \
  --exp-config "${CONFIG_PATH}" \
  RESULTS_DIR /app/result \
  LOG_FILE /app/result/challenge_eval.log
