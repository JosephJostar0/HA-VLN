# HA-VLN Challenge - Submission Format Specification

## Overview

选手需要提交**动作序列**文件。主办方将私有重放这些动作，计算所有评分指标。

## Submission Schema

### 文件格式
- **格式**: JSON
- **单位**: 
  - position: 米 (m)
  - heading: 弧度 (rad)
  - 动作代码: 整数

### JSON 结构

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [0, 2, 2, 1, 1, 3],
      "trajectory": [
        {
          "position": [6.307, 0.121, 0.185],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.407],
          "heading": -0.259,
          "stop": false
        }
      ]
    }
  ],
  "metadata": {
    "agent_name": "MyAgent",
    "timestamp": "2026-03-31T12:00:00Z",
    "split": "test"
  }
}
```

### 字段说明

#### 必填字段

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `episode_id` | string | 必填 | episode 唯一标识，与 test.json.gz 中的 episode_id 匹配 |
| `trajectory_id` | string | 必填 | trajectory 唯一标识，与 test.json.gz 中的 trajectory_id 匹配 |
| `scene_id` | string | 必填 | 场景 ID，与 test.json.gz 中的 scene_id 匹配 |
| `actions` | array[int] | 必填 | 动作序列，长度 > 0 且 ≤ 500 |

#### 动作代码 (Action Codes)

| 代码 | 动作名 | 描述 |
|------|--------|------|
| 0 | STOP | 停止导航，结束本 episode |
| 1 | MOVE_FORWARD | 前进 0.25m |
| 2 | TURN_LEFT | 左转 15° |
| 3 | TURN_RIGHT | 右转 15° |

#### 可选字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `trajectory` | array[dict] | 每步的观测状态（仅用于审计和可视化，不参与打分） |
| `trajectory[i].position` | array[float] | 第 i 步后的 xyz 坐标 |
| `trajectory[i].heading` | float | 第 i 步后的朝向（弧度，范围 [-π, π]） |
| `trajectory[i].stop` | bool | 该步后是否调用了 STOP 动作 |

#### Metadata

| 字段 | 类型 | 建议 | 说明 |
|------|------|------|------|
| `agent_name` | string | 是 | 你的方法/模型名称 |
| `timestamp` | string | 是 | 生成时间（ISO 8601 格式） |
| `split` | string | 是 | 总是 "test" |

---

## 验证规则 (Validator Rules)

选手提交将经过以下检查：

### 1. 结构验证
- ✓ 文件是有效的 JSON
- ✓ 根元素包含 `episodes` 字段且类型为 array
- ✓ 每个 episode 包含必填字段

### 2. 字段验证
- ✓ `episode_id`, `trajectory_id`, `scene_id` 都是字符串
- ✓ `actions` 是整数数组，每个动作 ∈ {0, 1, 2, 3}
- ✓ 轨迹长度 1 ≤ len(actions) ≤ 500

### 3. 数据完整性
- ✓ episode_id 来自 test 集（不能重复）
- ✓ 每个 episode_id 仅出现一次（无重复提交）
- ✓ test 集所有 episode 都被覆盖

### 4. 可选字段验证
- 若提供 `trajectory`：
  - 长度必须 ≥ 1（至少初始状态）
  - 每个点的 position 是长度为 3 的浮点数组
  - heading 范围 [-π, π]
  - stop 是布尔值

---

## 示例

### 最小化示例（仅动作）

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [1, 1, 1, 2, 2, 0]
    },
    {
      "episode_id": "1",
      "trajectory_id": "1234",
      "scene_id": "mp3d/GLvvgkT4dwJ/GLvvgkT4dwJ.glb",
      "actions": [3, 1, 0]
    }
  ],
  "metadata": {
    "agent_name": "SimpleAgent",
    "split": "test"
  }
}
```

### 完整示例（包含轨迹）

```json
{
  "episodes": [
    {
      "episode_id": "0",
      "trajectory_id": "5732",
      "scene_id": "mp3d/5ZKStnWn8Zo/5ZKStnWn8Zo.glb",
      "actions": [1, 1, 0],
      "trajectory": [
        {
          "position": [6.307, 0.121, 0.185],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.407],
          "heading": -0.259,
          "stop": false
        },
        {
          "position": [6.307, 0.121, 0.629],
          "heading": -0.259,
          "stop": true
        }
      ]
    }
  ],
  "metadata": {
    "agent_name": "HA-VLN-CMA",
    "timestamp": "2026-03-31T14:32:15Z",
    "split": "test"
  }
}
```

---

## 评测流程

1. **验证（Validator）**: 检查文件格式和完整性
2. **重放（Replayer）**: 在私有 simulator 中重放动作序列
3. **计算（Metric Engine）**: 计算 Success、SPL、nDTW、sDTW、TCR、SR_human 等指标
4. **聚合（Aggregator）**: 计算全集均值和统计
5. **报告（Reporter）**: 生成 leaderboard 结果和 per-episode 详情

结果将在以下方面返回：

- **公开指标** (Leaderboard): SR_human, SPL, nDTW, sDTW
- **诊断统计** (Per-episode JSON): 每个 episode 的完整指标、中间过程值
- **排行榜排序**: 
  1. 主排序：SR_human（成功率，人类感知安全）
  2. 次排序：SPL（路径效率）
  3. 三排序：nDTW（轨迹相似度）

---

## 常见问题 (FAQ)

**Q: 可否提交不同长度的轨迹？**  
A: 可以。每个 episode 的动作序列长度可以不同，但总长度不能超过 500 步。最后一个动作通常应该是 STOP。

**Q: 如果忘记在末尾加 STOP 怎么办？**  
A: Evaluator 会自动检测 episode 是否在 500 步后终止。如果未收到 STOP 信号，将视作 episode_over=False，可能得分偏低。

**Q: trajectory 字段是可选的吗？**  
A: 是。但提供 trajectory 有助于审计和可视化。如果提供，Evaluator 会校验其与 actions 的一致性。

**Q: 动作代码顺序是否固定？**  
A: 是。请严格按上表使用代码。其他值会触发验证错误。

**Q: 轨迹坐标精度有要求吗？**  
A: 建议保留小数点后 3 位。Evaluator 对浮点数精度不敏感，但过度四舍五入可能影响可视化。

---

## 提交清单

- [ ] 文件是有效的 JSON
- [ ] 所有必填字段已赋值
- [ ] episode_id 和 scene_id 与 test.json.gz 匹配
- [ ] 每个 actions 元素 ∈ {0, 1, 2, 3}
- [ ] actions 长度 ≤ 500
- [ ] 没有重复的 episode_id
- [ ] metadata 中 split 字段为 "test"
- [ ] （可选）若提供 trajectory，其字段格式与规范一致

---

**提交截止**: 见挑战赛公告  
**评测结果发布**: 用时通常 < 2 小时  
**申诉期限**: 结果发布后 7 天内可申诉
