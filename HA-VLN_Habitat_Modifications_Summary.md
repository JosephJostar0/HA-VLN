# HA-VLN 2.0: Habitat 修改与扩展分析

## 概述

HA-VLN 2.0 是一个基于 Habitat 的扩展项目，为视觉语言导航（VLN）添加了人类感知能力。项目通过二次封装而非直接修改 Habitat 核心代码的方式，实现了在连续和离散环境中动态多人类交互的仿真。

## 第一部分：HA-VLN 与 Habitat 的核心差异

### 1. 人类渲染系统 (Human Rendering System)

**核心组件：** `HASimulator/environments.py` 中的 `HAVLNCE` 类

**主要功能：**
- 管理 3D 人体模型的生命周期（加载、更新、移除）
- 使用子线程进行定时信号发送（0.1秒间隔，10Hz频率）
- 动态重新计算导航网格（navmesh）以处理碰撞
- 支持 120 帧人体运动序列的逐帧动画

**关键配置参数：**
```yaml
# HASimulator/config/HAVLNCE_task.yaml
SIMULATOR:
  ADD_HUMAN: True
  HUMAN_GLB_PATH: ../Data/HAPS2_0
  HUMAN_INFO_PATH: ../Data/Multi-Human-Annotations/human_motion.json
  RECOMPUTE_NAVMESH_PATH: ../Data/recompute_navmesh
```

### 2. 自定义测量指标 (Custom Measurements)

**新增指标：**
- `DistanceToHuman`: 计算智能体与人类之间的距离和角度关系
- `CollisionsDetail`: 增强的碰撞跟踪，支持逐步记录
- 人类感知评估指标：TCR（总碰撞减少）、CR（碰撞减少）、SR（考虑碰撞的成功率）

**注册方式：**
```python
# HASimulator/measures.py
@registry.register_measure
class DistanceToHuman(Measure):
    cls_uuid: str = "distance_to_human"
    # 实现细节...
```

### 3. 数据集扩展

**HA-R2R 数据集：**
- 基于 R2R 数据集的人类感知版本
- 包含人类活动描述的导航指令
- 支持多人类交互场景

**HAPS 2.0 数据集：**
- 72 个详细的人类运动序列（根据 human_motion.json）
- 使用 SMPL 参数表示人体形状和姿态
- 120 帧运动序列

**注意：** 论文中提到 HAPS 2.0 包含 486 个模型，但实际代码中使用的 human_motion.json 文件包含 72 个条目。这可能是因为：
1. 数据集有多个版本
2. 代码仅使用了部分数据
3. 486 是论文中的统计数字，包含所有变体

### 4. 离散环境支持 (HA-DE)

**核心组件：** `HASimulator/HA-DE/HASim.py` 中的 `HASimulator` 类

**功能特点：**
- 基于 Matterport3D Simulator 的扩展
- 使用命名管道（named pipes）进行进程间通信
- 支持实时渲染和离线渲染两种模式
- 人类状态与智能体视角同步

## 第二部分：从 Habitat 迁移到 HA-VLN

### 迁移步骤

#### 步骤 1：配置文件修改

**原始 Habitat 配置：**
```yaml
# 标准 VLN-CE 配置
BASE_TASK_CONFIG_PATH: configs/tasks/vlnce_task.yaml
```

**修改为 HA-VLN 配置：**
```yaml
# HA-VLN 配置
BASE_TASK_CONFIG_PATH: ../HASimulator/config/HAVLNCE_task.yaml
```

#### 步骤 2：添加依赖导入

在 agent 代码中添加：
```python
import sys
sys.path.append('./HASimulator')  # 添加 HASimulator 模块路径
```

#### 步骤 3：启用人类渲染

确保任务配置包含：
```yaml
TASK:
  MEASUREMENTS: [
    DISTANCE_TO_GOAL,
    SUCCESS,
    SPL,
    PATH_LENGTH,
    ORACLE_SUCCESS,
    STEPS_TAKEN,
    COLLISIONS,
    COLLISIONS_DETAIL,
    DISTANCE_TO_HUMAN  # 新增的人类感知指标
  ]
```

#### 步骤 4：数据准备

下载并放置以下数据：
```
Data/
├── HAPS2_0/                    # 3D 人体模型
├── Multi-Human-Annotations/    # 人类运动标注
├── HA-R2R/                    # 人类感知导航指令
└── recompute_navmesh/         # 动态导航网格缓存
```

### 配置对比表

| 配置项 | Habitat VLN-CE | HA-VLN-CE | 说明 |
|--------|----------------|-----------|------|
| BASE_TASK_CONFIG_PATH | configs/tasks/vlnce_task.yaml | ../HASimulator/config/HAVLNCE_task.yaml | 基础任务配置路径 |
| SIMULATOR.ADD_HUMAN | 不存在 | True/False | 人类渲染开关 |
| HUMAN_GLB_PATH | 不存在 | ../Data/HAPS2_0 | 人体模型路径 |
| TASK.MEASUREMENTS | 标准指标集 | 添加 DISTANCE_TO_HUMAN | 测量指标扩展 |

## 第三部分：Agent 与 HA-VLN-CE 的交互示例

### 交互架构图

```
Agent (VLN-CE)
    ↓
Habitat 标准 API
    ↓
HAVLNCE 环境包装器
    ↓
Habitat-Sim (带人类模型)
    ↓
观测数据 (包含人类位置信息)
```

### 精确到函数的调用流程

#### 1. 配置加载阶段

**文件：** `agent/run.py`
```python
def run_exp(exp_config: str, run_type: str, opts=None) -> None:
    config = get_config(exp_config, opts)  # 加载配置
    # config.BASE_TASK_CONFIG_PATH 指向 HASimulator/config/HAVLNCE_task.yaml
```

**文件：** `agent/VLN-CE/vlnce_baselines/config/default.py`
```python
def get_config(config_paths=None, opts=None):
    # 合并基础配置和覆盖配置
    # 关键：BASE_TASK_CONFIG_PATH 决定了使用哪个环境配置
```

#### 2. 环境初始化阶段

**文件：** `HASimulator/environments.py`
```python
class HAVLNCE():
    def __init__(self, config: Config, sim):
        self._config = config
        self._sim = sim
        self._initialize_simulator_resources()  # 加载人类运动数据
        self.__init_manager__()  # 初始化对象模板管理器
        
        # 启动信号发送线程
        self._signal_thread = threading.Thread(target=self._signal_sender)
        self._signal_thread.daemon = True
        self._signal_thread.start()
    
    def _initialize_simulator_resources(self):
        """加载人类运动数据和资源"""
        self.human_motion_json_path = self._config.SIMULATOR.HUMAN_INFO_PATH
        self.data_path = self._config.SIMULATOR.HUMAN_GLB_PATH
        with open(self.human_motion_json_path, 'r') as f:
            self.human_motion_data = json.load(f)
```

#### 3. 训练循环中的交互

**文件：** `agent/VLN-CE/vlnce_baselines/agents/` (示例训练器)
```python
class MyTrainer:
    def train(self):
        while not self.is_done():
            # 标准 Habitat 训练循环
            observations = self.env.reset()  # 重置环境
            
            # HAVLNCE.reset() 被调用，触发人类模型刷新
            # 1. 清除信号队列
            # 2. 发送 REFRESH_HUMAN_MODEL 信号
            # 3. 添加新的人类模型
            
            for step in range(self.max_steps):
                action = self.policy(observations)
                observations, reward, done, info = self.env.step(action)
                
                # info 中包含了人类感知指标
                # info['distance_to_human']: 与各人类的距离和角度
                # info['collisions_detail']: 碰撞详情
```

#### 4. 观测数据流

**人类位置信息的传递：**
```python
# 在 HAVLNCE.add_new_human_model() 中
self._sim._human_posisions = human_positions  # 存储人类位置到 simulator

# 在 DistanceToHuman.update_metric() 中
human_positions = self._sim._human_posisions  # 从 simulator 获取
for name, (position, rotation) in human_positions.items():
    distance_to_human = euclidean_distance(current_position, position)
    # 计算角度关系...
    self._metric[name] = (distance_to_human, theta)
```

#### 5. 人类模型更新机制

**线程通信模式：**
```python
def _signal_sender(self):
    """子线程函数，每0.1秒发送信号（10Hz频率）"""
    while True:
        self.signal_queue.put('REFRESH_HUMAN_MODEL', timeout=1)
        self.total_signals_sent += 1
        time.sleep(0.1)  # 控制更新频率（实际代码为0.1秒）

def _handle_signals(self):
    """主线程处理信号"""
    while not self.signal_queue.empty():
        signal = self.signal_queue.get_nowait()
        frame_id = (self.total_signals_sent - 1) % 120
        self.refresh_human_model(frame_id)  # 刷新人类模型
```

**注意：** 源代码中存在文档字符串与实际代码不一致的情况：
- 文档字符串写的是"every 0.5 seconds"
- 实际代码是`time.sleep(0.1)`，即0.1秒间隔

### 关键 API 调用示例

#### 场景 1：获取人类感知观测

```python
# Agent 代码示例
import habitat
from habitat.config import Config
from habitat.core.env import Env

# 加载 HA-VLN 配置
config = habitat.get_config("agent/config/cma_pm_da_aug_tune.yaml")

# 创建环境
env = Env(config=config)

# 重置环境（触发人类模型初始化）
observations = env.reset()

# 执行动作
action = env.action_space.sample()
observations, reward, done, info = env.step(action)

# 访问人类感知信息
if 'distance_to_human' in info:
    for human_name, (distance, angle) in info['distance_to_human'].items():
        print(f"Human {human_name}: distance={distance:.2f}m, angle={angle:.1f}°")

if 'collisions_detail' in info:
    print(f"Collision count: {info['collisions_detail']['count']}")
```

#### 场景 2：自定义人类感知策略

```python
class HumanAwarePolicy:
    def __init__(self, config):
        self.safe_distance = 2.0  # 安全距离阈值
        self.max_angle = 45.0     # 最大可接受角度
    
    def act(self, observations, info):
        # 检查人类距离
        if 'distance_to_human' in info:
            for human_name, (distance, angle) in info['distance_to_human'].items():
                if distance < self.safe_distance and abs(angle) < self.max_angle:
                    # 人类太近且在视野内，执行避让动作
                    return self.get_avoidance_action(human_name, distance, angle)
        
        # 正常导航策略
        return self.normal_navigation(observations)
```

## 第四部分：架构设计模式

### 1. 包装器模式 (Wrapper Pattern)

HA-VLN 使用包装器模式扩展 Habitat：
- `HAVLNCE` 包装 Habitat-Sim，添加人类渲染功能
- 自定义 Measurements 通过 Habitat 的注册系统集成
- 配置驱动，无需修改核心代码

### 2. 线程安全设计

人类渲染使用生产者-消费者模式：
- **生产者：** `_signal_sender` 线程定期发送更新信号
- **消费者：** `_handle_signals` 在主线程处理信号
- **同步机制：** `threading.Lock` 保护人类模型操作

### 3. 数据驱动配置

所有人类相关参数通过配置文件管理：
```yaml
SIMULATOR:
  ADD_HUMAN: True                    # 开关
  HUMAN_GLB_PATH: ../Data/HAPS2_0    # 模型路径
  HUMAN_INFO_PATH: ../Data/Multi-Human-Annotations/human_motion.json  # 运动数据
  RECOMPUTE_NAVMESH_PATH: ../Data/recompute_navmesh  # 导航网格缓存
  HUMAN_COUNTING: True               # 人类计数功能
```

### 4. 模块化扩展

项目结构支持模块化扩展：
```
HA-VLN/
├── HASimulator/          # 仿真器扩展
│   ├── environments.py   # HAVLNCE 类
│   ├── measures.py       # 自定义测量
│   ├── detector.py       # 视觉检测
│   └── config/           # 任务配置
├── agent/                # 智能体实现
│   └── VLN-CE/           # 基于 VLN-CE 的智能体
└── Data/                 # 数据集
```

## 第五部分：常见问题与解决方案

### Q1: 如何禁用人类渲染？

**解决方案：**
```yaml
# 在任务配置中设置
SIMULATOR:
  ADD_HUMAN: False
```

### Q2: 人类模型加载失败？

**检查步骤：**
1. 确认 `HUMAN_GLB_PATH` 路径正确
2. 验证 `human_motion.json` 文件格式
3. 检查 GLB 模型文件完整性

### Q3: 性能问题？

**优化建议：**
1. 调整 `time.sleep(0.1)` 中的等待时间（源代码中的实际值）
2. 启用导航网格缓存（`RECOMPUTE_NAVMESH_PATH`）
3. 减少同时渲染的人类数量

### Q4: 如何添加新的人类动作？

**扩展流程：**
1. 在 HAPS 2.0 数据集中添加新动作
2. 更新 `human_motion.json` 标注文件
3. 将 GLB 模型放入对应目录

## 总结

HA-VLN 2.0 通过精心设计的二次封装，在保持 Habitat 兼容性的同时，添加了全面的人类感知能力。关键设计决策包括：

1. **非侵入式扩展**：通过包装器和配置系统，避免修改 Habitat 核心
2. **线程安全渲染**：分离渲染逻辑与主仿真循环
3. **数据驱动配置**：所有人类参数通过 YAML 配置管理
4. **模块化架构**：清晰分离仿真器、智能体和数据集

对于希望从标准 Habitat 迁移到 HA-VLN 的用户，主要需要：
1. 更新配置文件指向 HA-VLN 任务配置
2. 导入 HASimulator 模块
3. 准备人类模型和标注数据
4. 在智能体策略中利用人类感知信息

这种设计使得 HA-VLN 既可以作为独立的人类感知导航基准测试平台，也可以作为 Habitat 的扩展库集成到现有项目中。