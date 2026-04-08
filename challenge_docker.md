# HA-VLN Challenge 2026 Docker Guide

This repository's Docker workflow is based on the official prebuilt image used for challenge evaluation. The local participant setup and the official evaluator stay aligned at the compose level, while the mounted `Data` content differs between participant-side local testing and organizer-side final scoring.

## Evaluation Image

Pull the official image before running the compose service:

```bash
docker pull ghcr.io/josephjostar0/havln-eval-image:latest
```

The compose template is defined in `docker-compose-template.yml`. Copy it to `docker-compose.yml`, then replace the host-side paths in `volumes` with your absolute local paths:

```bash
cp docker-compose-template.yml docker-compose.yml
```

## Configure Mounts

The compose service mounts three participant-controlled paths:

1. `Data -> /app/Data:ro`
   The dataset and simulator assets used by the mounted challenge environment. This mount is read-only. Participant-side local packages are expected to contain the public data needed for development and validation, such as `train`, `val_seen`, and `val_unseen`.
2. `agent -> /app/agent:rw`
   Your submission directory. The container starts from `/app/agent/run.sh`. It is mounted read-write in the current validated setup, so your code can create temporary files here if needed.
3. `result -> /app/result:rw`
   A writable output directory intended for exported predictions, logs, or copied final artifacts.

The current compose configuration keeps the official simulator stack inside the image and mounts only participant inputs and outputs from the host.

After updating the mount paths, start the evaluation container with:

```bash
docker compose up
```

The image contains the official simulator stack and its required runtime dependencies. Baseline agents may be documented elsewhere in this repository, but they are not packaged into this challenge Docker image. If your submission needs extra Python packages or other runtime setup, do that from `/app/agent/run.sh`.

## Manual Debugging Inside The Container

The service normally runs:

```bash
bash /app/agent/run.sh
```

If you want an interactive shell instead of immediately executing `run.sh`, override the service entrypoint:

```bash
docker compose run --rm --entrypoint bash evaluator
```

This is the recommended way to inspect the mounted files, verify Python environments, and manually debug your own submission inside the official image.

Before debugging your agent inside the container, do not forget to install the dependencies required by your own submission, for example from your agent's `requirements.txt`.

For example, after entering the container you can inspect the default environment and your mounted submission with commands such as:

```bash
cd /app
conda env list
ls /app/agent
```

## Public Data Versus Final Scoring Data

Participants should assume they only receive the public development data needed for training and validation, namely the public training split and the public seen/unseen validation splits.

Final scoring is performed by the organizers with separate non-public data mounted into the same `/app/Data` location. Participant documentation should treat that scoring data as internal and not rely on any private split details.

## Submission Expectations

The exact submission package format and scoring interface are still TBA and may change as the automated evaluation pipeline is finalized.

Your submission directory should include a `run.sh` entry script. That script is the right place to:

- activate environments if needed
- install extra dependencies required by your own agent
- launch your own submission logic
- redirect outputs to `/app/result` when you want artifacts copied back to the host

The challenge Docker image is intentionally focused on simulator compatibility and evaluation stability, not on pre-packaging every possible participant agent environment.
