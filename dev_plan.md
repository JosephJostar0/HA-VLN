**dev_plan.md (content)**

## Plan: HA-VLN Timing-Aware Submission SDK (English)

**Goal**  
Provide an official, model-agnostic SDK to record actions and per-step elapsed time (`dts`) for challenge submissions, without running participant code on organizer servers. Support any custom agent (e.g., ETPNav) while keeping simulator core clean.

---

### 1. Submission Schema Update

**Add required field**  
- `dts`: array of floats (seconds), same length as `actions`.  
- Each `dts[i]` is elapsed time between action `i-1` and action `i`.

**Timing rule for replay**  
- Maintain a cumulative timer.  
- Each time cumulative `dts` crosses `0.1s`, advance human frame by 1.  
- If a single `dts` is large, advance multiple frames accordingly.

---

### 2. SDK Location & API

**Location**  
- Top-level, model-agnostic: `sdk/` (preferred) or `tools/`.  
- No dependency on any baseline agent code.

**Minimal API (example)**  
- `init_run(metadata)`  
- `start_episode(episode_id, trajectory_id, scene_id)`  
- `record_step(action, dt, position=None, heading=None, stop=False)`  
- `end_episode()`  
- `export_submission(path)`

---

### 3. Optional Simulator Hook (Callback)

**Purpose**  
Make logging easy for anyone who uses HASimulator, without hard-wiring submission logic into simulator core.

**Design**  
- Add optional `step_callback` (callable or list) on `HAVLNCE`.  
- Default: `None` (no impact if unused).  
- Trigger after `_handle_signals()` and after `sim.step(action)`.

**Callback payload (minimal)**  
- `action`  
- `dt`  
- `frame_id`  
- `agent_state` (`position`, `heading`)  
- `episode_id`, `scene_id` if available (may be `None`)

---

### 4. Integration Examples

Provide code snippets for:
- Baseline CMA inference loop  
- ETPNav-style loop  
- Any custom agent using Habitat `Env`

---

### 5. Validator & Examples

Update validator to enforce:
- `dts` exists and length == `actions` length  
- each `dts[i] > 0`  
- optional upper bound (e.g., `dts[i] <= 10s`) if desired

Update example submissions to include `dts`.

---

### 6. Documentation

Update:
- Submission format doc  
- Integration guide (with SDK usage examples)

---

### 7. Verification Checklist

- Generate a submission with SDK and validate successfully.  
- Confirm `dts` matches `actions` length.  
- Confirm replay logic uses cumulative time for human frame updates.

---

## 计划：HA‑VLN 计时提交 SDK（中文）

**目标**  
提供官方、模型无关的SDK，用于记录 `actions` 与每步耗时 `dts`，无需主办方执行参赛者代码。支持任意自带agent（如ETPNav），同时保持仿真核心清洁。

---

### 1. 提交格式更新

**新增必填字段**  
- `dts`：浮点数组（秒），长度与 `actions` 相同。  
- `dts[i]` 表示第 `i` 步动作与前一步之间的耗时。

**回放规则**  
- 维护累计时间。  
- 累计时间每跨过 `0.1s` 推进一次人类帧。  
- 单步 `dts` 很大时可推进多帧。

---

### 2. SDK 位置与接口

**位置**  
- 顶层、模型无关：`sdk/`（优先）或 `tools/`。  
- 不依赖任何baseline代码。

**最小接口示例**  
- `init_run(metadata)`  
- `start_episode(episode_id, trajectory_id, scene_id)`  
- `record_step(action, dt, position=None, heading=None, stop=False)`  
- `end_episode()`  
- `export_submission(path)`

---

### 3. 可选的仿真回调（Callback）

**目的**  
让使用 HASimulator 的人更容易记录，但不把提交逻辑硬写入仿真核心。

**设计**  
- 在 `HAVLNCE` 上增加可选 `step_callback`（函数或列表）。  
- 默认 `None`（不使用时无影响）。  
- 在 `_handle_signals()` 后、`sim.step(action)` 后触发。

**回调参数（最小）**  
- `action`  
- `dt`  
- `frame_id`  
- `agent_state`（`position`、`heading`）  
- `episode_id`、`scene_id`（如果可用，否则为 `None`）

---

### 4. 集成示例

提供代码片段：
- CMA baseline 推理循环  
- ETPNav 风格循环  
- 任意基于 Habitat `Env` 的自定义agent

---

### 5. 校验器与示例文件

校验新增：
- `dts` 必须存在且长度等于 `actions`  
- 每个 `dts[i] > 0`  
- 可选上限（如 `dts[i] <= 10s`）

更新示例提交文件，加入 `dts`。

---

### 6. 文档更新

更新：
- 提交格式文档  
- 集成指南（包含 SDK 使用方式）

---

### 7. 验证清单

- 用 SDK 生成提交文件并通过校验。  
- 确认 `dts` 与 `actions` 长度匹配。  
- 确认回放使用累计时间推进人类帧。
