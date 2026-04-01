# HA-R2R 挑战说明（主办方/选手数据划分）

## 1. 数据集与挑战简介

HA-R2R（Human-Aware Room-to-Room）是一个面向视觉语言导航（VLN）的数据集，核心目标是评测智能体在“带有人类活动干扰与社会交互语义”的室内场景中，是否能够根据自然语言指令完成导航。

与传统 VLN 任务相比，HA-R2R 指令中不仅描述路径与地标，还包含人类行为信息（如对话、活动、聚集、潜在阻挡等），更强调人机共处场景下的导航鲁棒性与行为合理性。

挑战赛目标是：
- 让选手基于训练/验证数据训练模型；
- 在盲测测试集上仅做推理输出轨迹；
- 由主办方使用保留真值数据进行统一离线评分，得到可公平比较的排行榜结果。

---

## 2. 发给选手的内容

选手可获得并使用以下内容：

### 2.1 训练与开发数据
- `Data/HA-R2R/train/train.json.gz`
- `Data/HA-R2R/val_seen/val_seen.json.gz`
- `Data/HA-R2R/val_unseen/val_unseen.json.gz`

可选（如需 BERT 词表索引版本）：
- `Data/HA-R2R/train/train_bertidx.json.gz`
- `Data/HA-R2R/val_seen/val_seen_bertidx.json.gz`
- `Data/HA-R2R/val_unseen/val_unseen_bertidx.json.gz`

### 2.2 测试推理数据（非 GT）
- `Data/HA-R2R/test/test.json.gz`
- 或 `Data/HA-R2R/test/test_bertidx.json.gz`

说明：
- 测试非 GT 文件用于盲测推理；
- 选手应提交每个测试 episode 的预测轨迹/动作序列（按主办方规定格式）。

### 2.3 非 GT 文件包含什么 / 不包含什么

以 `test.json.gz` 为例，非 GT 测试文件通常包含：
- `episode_id`
- `trajectory_id`
- `scene_id`
- `instruction`（文字指令）
- `start_position` 与 `start_rotation`
- `reference_path`（仅保留起点，长度通常为 1）

非 GT 测试文件不包含：
- `goals`（目标点真值）
- `info`（如 geodesic_distance 等附加真值信息）

这意味着选手可以完成“推理与提交轨迹”，但无法仅凭非 GT 文件本地复现完整官方指标。

---

## 3. 留给主办方的内容

主办方保留以下真值与评测依赖文件，不向选手公开：

### 3.1 测试真值文件（核心）
- `Data/HA-R2R/test/test_gt.json.gz`
- `Data/HA-R2R/test/test_gt_bertidx.json.gz`

用途：
- 提供目标与参考路径真值；
- 离线计算 SR / SPL / NDTW / SDTW 等排行榜指标。

GT 文件相对非 GT 的关键差异：
- 包含 `goals`（用于成功判定、距离相关指标等）
- `reference_path` 为完整路径（而非仅起点）
- 与非 GT 版本的同一 `episode_id` 共享相同场景、起点与指令文本，但包含额外打分真值

### 3.3 数据重叠验证（防止泄漏）

为确保挑战划分合理，需要明确“按什么键判重”。

推荐判重键（强到弱）：
1. `scene_id + trajectory_id`
2. `scene_id + start_position + start_rotation + reference_path`
3. `instruction_text`

已验证结论：
1. `test` 与 `train / val_seen / val_unseen` 在 `scene_id + trajectory_id` 上重叠为 0。
2. `test` 与 `train / val_seen / val_unseen` 在 `instruction_text` 上重叠为 0。
3. `test_gt` 与 `train / val_seen / val_unseen` 在强键（`scene_id + start + rotation + reference_path`）上重叠为 0。

注意事项：
1. `episode_id` 在不同 split 中会复用，不能作为全局唯一键做泄漏判断。
2. `test` 与 `test_gt` 属于同一批测试样本（场景、起点、指令一致），但 `test` 的 `reference_path` 通常仅保留起点，而 `test_gt` 保留完整路径并含 `goals`。

### 3.2 评测辅助文件（按规则决定是否公开）
- `Data/HA-R2R-tools/` 下的评测辅助统计文件（如碰撞相关统计）

用途：
- 支撑扩展指标或主办方内部统计；
- 若公开，需在赛制中明确其用途与边界。

---

## 4. 公平性与流程建议

建议采用以下标准流程：
1. 选手仅使用 train/val 训练与调参。
2. 选手仅在 test（非 GT）上推理并提交结果。
3. 主办方使用 test_gt 私有打分脚本统一评测。
4. 排行榜仅发布由主办方私有评测得到的结果。

可对外公布的简版口径：
1. 非 GT 测试包 = “可推理，不可完整打分”。
2. GT 测试包 = “仅主办方持有，用于统一打分”。
3. 选手提交预测结果，主办方回传指标与排名。

该流程可避免测试真值泄露，保证不同方法在同一盲测标准下可公平比较。
