import distutils.version
import torch
import numpy as np
from gym import spaces
from habitat.config.default import Config
from vlnce_baselines.models.etpnav_policy import PolicyViewSelectionETP

def test_policy():
    print("开始测试 ETPNav Policy 实例化...")
    
    # 1. 伪造一个 Config
    mock_config = Config()
    mock_config.defrost()
    mock_config.TORCH_GPU_ID = 0
    
    mock_config.MODEL = Config()
    mock_config.MODEL.TORCH_GPU_ID = 0
    
    # --- 关键修改：添加 ETPNav 所需的参数 ---
    # 预训练权重的路径，这里可以先填一个不存在的假路径，
    # 只要让代码不因为找不到这个“变量名”而崩溃即可。
    mock_config.MODEL.pretrained_path = "data/vlnbert/pretrained_model.bin" 
    
    # ETPNav 通常需要指定任务类型
    mock_config.MODEL.task_type = 'r2r' 
    mock_config.MODEL.spatial_output = True
    
    # 深度编码器配置 (保持之前的)
    mock_config.MODEL.DEPTH_ENCODER = Config()
    mock_config.MODEL.DEPTH_ENCODER.cnn_type = "VlnResnetDepthEncoder"
    mock_config.MODEL.DEPTH_ENCODER.output_size = 128
    mock_config.MODEL.DEPTH_ENCODER.backbone = "resnet50"
    mock_config.MODEL.DEPTH_ENCODER.ddppo_checkpoint = "data/ddppo-models/gibson-2plus-resnet50.pth"
    
    # RGB 编码器配置 (ETPNav 可能也需要)
    mock_config.MODEL.RGB_ENCODER = Config()
    mock_config.MODEL.RGB_ENCODER.cnn_type = "TorchVisionResNet50" # 或者 "CLIPEncoder"
    mock_config.MODEL.RGB_ENCODER.output_size = 256
    
    mock_config.freeze()

    # 2. 伪造 Observation Space (假装传感器看到了东西)
    # HAVLN 通常输入 224x224 或 256x256 的图像
    obs_space = spaces.Dict({
        "rgb": spaces.Box(low=0, high=255, shape=(224, 224, 3), dtype=np.uint8),
        "depth": spaces.Box(low=0.0, high=1.0, shape=(256, 256, 1), dtype=np.float32),
        "instruction": spaces.Discrete(5401) # 词表大小
    })

    # 3. 伪造 Action Space (通常 R2R 有 4-6 个离散动作，或者动态 action)
    action_space = spaces.Discrete(4)

    # 4. 尝试实例化模型
    try:
        policy = PolicyViewSelectionETP.from_config(
            config=mock_config,
            observation_space=obs_space,
            action_space=action_space
        )
        print("✅ 模型实例化成功！没有缺失依赖。")
        
        # 5. 可选：喂入假数据测试 Forward (这里先跳过复杂的 mode 分支，只看能不能移到 GPU)
        policy = policy.to(torch.device("cuda:0" if torch.cuda.is_available() else "cpu"))
        print(f"✅ 模型已成功移动到: {policy.net.device}")
        
    except Exception as e:
        print("❌ 测试失败，报错信息如下：")
        print(e)

if __name__ == "__main__":
    test_policy()