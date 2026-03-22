# Repo
```shell
$ tree -L 1
.
├── Data        # 数据。存放静态场景网格(MP3D)、动态人体动作模型(HAPS 2.0)、导航指令集(HA-R2R)及预训练权重。
├── HASimulator # 仿真。基于Habitat封装，负责加载场景与动态人物、计算实时物理碰撞，并渲染输出机器人视角的观测(RGB/Depth/计数)。
├── agent       # 智能体算法。包含多模态模型架构(如CMA)、特征编码器以及强化/模仿学习的训练与推理代码。
├── demo        # 存放项目README和展示页面使用的各种GIF动图和静态图表。
└── scripts     # 系统的交互测试(demo.py)、场景人物数据融合预处理(human_scene_fusion.py)以及数据下载脚本。
```

## Data
```shell
Data/
├── HA-R2R                  # 导航指令数据集。包含融入了"人类活动描述"的路径文本指令（如训练集、验证集）。
├── HA-R2R-tools            # 指令处理与评估工具。包含文本特征嵌入（Embeddings）和碰撞统计等相关数据文件。
├── HA-VLN-DE               # 离散环境数据（Discrete Environment）。针对离散图节点导航任务的数据版本。
├── HAPS2_0                 # 动态人物动作资产库。存放大量高精度的 3D 人体模型及骨骼动画序列（如看书、跑步）。
├── Multi-Human-Annotations # 人物位置与交互标注。核心配置文件（human_motion.json），定义了人物在哪个房间、做什么动作。
├── ddppo-models            # 预训练视觉权重。存放用于提取环境深度图（Depth）特征的 ResNet 预训练模型。
├── recompute_navmesh       # 导航网格缓存。存放仿真器加入人物模型后实时计算并保存的 NavMesh，用于物理碰撞计算。
└── scene_datasets          # 静态房间场景库。存放下载的 Matterport3D (MP3D) 房屋 3D 网格和语义分割数据。
```

## HASimulator
```shell
HASimulator/
├── GroundingDINO # 视觉目标检测框架。集成用于在机器人的第一人称视角中识别并统计视野内的人物数量（human_counting API）。
├── HA-DE         # 离散环境（Discrete Environment）仿真引擎。包含基于全景图和导航网格的底层 C++ 引擎（Matterport3DSimulator）及相关的离散导航任务代码。
└── config        # 仿真任务配置文件。存放 YAML 格式的文件，用于定义机器人挂载的传感器、是否开启人物渲染（ADD_HUMAN）、以及评估指标等设定。
```

### enviroments.py
```shell
environments.py
└── class HAVLNCE                          # 核心环境扩展类，负责将动态人类活动融入静态房间
    ├── __init__ & __init_manager__        # 初始化阶段。加载动作数据(JSON)、预载所有 3D 人物模型模板(GLB)，并启动后台信号子线程。
    ├── reset                              # 回合重置。清空信号队列、帧数归零，并在初始位置（第0帧）加载人物模型。
    ├── _signal_sender                     # 后台“时钟”子线程。通过一个死循环，每隔 0.1 秒向主线程队列发送一个刷新信号。
    ├── _handle_signals                    # 主线程信号接收器。计算当前帧数(frame_id)，触发人物刷新，并负责重算/加载最新的导航网格(NavMesh)。
    ├── refresh_human_model                # 刷新调度器。按顺序依次调用“移除旧模型”和“添加新模型”。
    ├── remove_previous_human_model        # 销毁实例。遍历上一帧记录的 object_ids，把旧姿态的 3D 小人从物理引擎中彻底删除。
    └── add_new_human_model                # 生成实例。根据帧数读取位置(translation)和欧拉角旋转，转换为四元数后将新姿态的小人渲染到场景中，并加入碰撞检测。
```

### detector.py
```shell
detector.py
├── plot_boxes_to_image                    # 图像渲染辅助函数。负责把大模型检测到的物体边界框（Bounding Box）画在第一人称图像上。
├── load_image                             # 数据预处理函数。将机器人的视觉观测（PIL Image）转换为适合模型输入的张量（Tensor），并做标准化。
├── load_model                             # 模型加载器。根据配置和权重路径，初始化并加载 GroundingDINO 模型。
└── class Detector                         # 核心视觉感知类（继承自 nn.Module），充当机器人的“高级视觉”
    ├── __init__                           # 初始化。加载并配置本地的 GroundingDINO_SwinT 权重，设置检测阈值（box_threshold, text_threshold）。
    └── forward                            # 前向传播。
                                           # 1. 接收机器人的 RGB 图像和文本提示（caption，例如 "person"）。
                                           # 2. 运行模型预测，输出画面中“人”的位置和数量。
                                           # 3. 将计数结果记录到统计信息（stats_info['human_counting']）中，并返回画好框的图片。
```

### metric.py
```shell
metric.py
└── class Calculate_Metric                 # 自定义评估指标类，负责给机器人的导航表现“打分”
    ├── __init__                           # 初始化。根据数据集划分（train/val/test），加载对应的预计算“原生碰撞”基线文件。
    └── __call__                           # 核心计算逻辑。当一个 episode 结束时被调用：
                                           # 1. TCR (True Collision Rate): 扣除静态环境的“原生碰撞”后，计算真正撞到人的次数。
                                           # 2. CR (Collision Rate): 只要额外撞人次数大于0，就算发生碰撞 (设为1)。
                                           # 3. SR (Success Rate): 必须在成功到达终点的同时且完全没撞到人 (TCR==0)，才算真正成功。
```


## Agent
```shell
agent/                          # 智能体算法层（机器人的“大脑”），负责接收视觉/文本输入并输出导航动作。
├── VLN-CE                      # 底层依赖框架。基于经典的“连续环境视觉语言导航”框架进行二次开发。
│   ├── data                    # 基础框架的运行输出目录。
│   │   ├── checkpoints         # 模型训练时保存的权重文件（.pth）。
│   │   ├── logs                # 训练过程的文本日志。
│   │   ├── tensorboard_dirs    # 用于 TensorBoard 监控损失函数和训练曲线的数据。
│   │   ├── trajectories_dirs   # 保存智能体在环境中走过的路径坐标数据。
│   │   └── videos              # 测试或推理时渲染出的第一人称导航演示视频。
│   ├── habitat_extensions      # 环境扩展模块。对 Habitat 仿真器的动作、传感器和评估指标进行定制。
│   │   └── config              # 扩展任务的相关配置（如定义奖励函数或观测空间）。
│   └── vlnce_baselines         # 核心基线算法与模型库（如强化学习/模仿学习的代码）。
│       ├── common              # 通用工具（如数据加载、环境封装、轨迹存储器 Rollout Storage）。
│       ├── config              # 各种基线网络（CMA、Seq2Seq等）的超参数配置文件。
│       ├── models              # PyTorch 神经网络架构定义（包含视觉编码器、文本编码器和跨模态决策网络）。
│       └── waypoint_pred       # 航点预测模块（在连续环境中预测智能体下一步可以走向的局部目标点）。
├── config                      # HA-VLN 专属实验配置。存放如 README 中提到的模型训练配置文件（.yaml）。
└── data                        # HA-VLN 专属实验的输出结果目录。
    ├── logs                    # 实验主日志目录。
    │   ├── checkpoints         # HA-VLN 训练过程中保存的最佳模型参数。
    │   ├── eval_results        # 模型在各个验证集（如 Seen/Unseen）上的评估指标得分（如 SR, CR 等）。
    │   └── tensorboard_dirs    # HA-VLN 实验的 TensorBoard 记录。
    └── trajectories_dirs       # 推理阶段生成的详细导航路径数据。
        └── debug               # 调试用的特定轨迹缓存。
```

```shell
agent/
├── run.py                             # 整个智能体训练与测试的入口脚本。负责解析参数、构建环境，并实例化对应的 Trainer。
├── config/                            # HA-VLN 任务专属的 YAML 配置文件（定义学习率、批次大小、使用什么传感器等）。
├── data/                              # 存放训练跑出来的 checkpoints（模型权重）和 TensorBoard 日志。
└── VLN-CE/                            # 视觉语言导航的基础算法框架
    ├── habitat_extensions/            # 环境适配器。定义机器人在 Habitat 里能做什么动作（如前进、转向）以及如何处理观测数据。
    └── vlnce_baselines/               # 核心算法与模型库
        ├── models/                    # 神经网络架构区
        │   ├── cma_policy.py          # -> 跨模态注意力决策大脑 (Cross-Modal Attention)。
        │   ├── seq2seq_policy.py      # -> 传统的序列到序列备选大模型。
        │   └── encoders/              # -> 各种“感官”特征提取器（文本 Instruction、视觉 ResNet/ViT）。
        ├── common/                    # 强化/模仿学习组件库
        │   ├── rollout_storage.py     # -> 经验池/轨迹存储。机器人在环境里试错的每一步（State, Action, Reward）都存这里。
        │   ├── env_utils.py           # -> 多进程环境封装。为了训练快，通常会同时开好几个仿真房间让机器人并行跑。
        │   └── aux_losses.py          # -> 辅助损失函数（比如我们刚才在 CMA 里看到的 Progress Monitor 进度预测）。
        ├── dagger_trainer.py          # 模仿学习训练器 (DAgger 算法)。靠"最短路径"教机器人怎么走。
        └── ddppo_waypoint_trainer.py  # 强化学习训练器 (DDPPO 算法)。靠机器人自己在环境里瞎撞，根据 Reward 更新策略。
```
