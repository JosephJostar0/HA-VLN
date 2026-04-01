# Trajectory Logging for HA-VLN Challenge

This note records the minimum trajectory elements needed for reliable, offline evaluation in HA-VLN.

## Required Elements (Minimum Set)

1. episode_id
- Reason: identifies the exact episode (scene, start position, start rotation, goal, instruction) in the fixed dataset. This lets the evaluator load the same episode deterministically without relying on random sampling.

2. action sequence (per step)
- Reason: collisions and other physics-based metrics are computed per step from the simulator. A position-only trace cannot recover whether a MOVE_FORWARD action was blocked, clipped, or resulted in a collision.
- Action space in HA-VLN-CE: STOP, MOVE_FORWARD, TURN_LEFT, TURN_RIGHT.

3. per-step timestamp (relative to episode start)
- Reason: human motion advances on wall-clock time in HA-VLN-CE. The timestamp allows the evaluator to replay actions at the same cadence and re-synchronize human state updates.

## Optional but Recommended

4. per-step position (agent global position)
- Reason: debugging, sanity checks, and post-hoc consistency verification against replay results.

5. per-step heading (agent orientation)
- Reason: helps validate that replayed trajectories match submitted traces, especially when collisions or turning behaviors are involved.

## Why These Are Needed for Metric Recalculation

- Collisions, TCR/CR/SR: require step-level physics results and cannot be reliably inferred from geometry-only traces.
- Human-aware metrics: depend on real-time human state, which is tied to timestamps rather than step count.
- Reproducibility: episode_id + actions + timestamps allow a deterministic replay on the official evaluator without access to the submitter's model.

## Summary of the Minimal Submission

- episode_id
- steps[]: { action, timestamp_ms }

## Recommended Submission (Full Trace)

- episode_id
- steps[]: { action, timestamp_ms, position, heading }
