import distutils.version
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from habitat.config.default import Config
from habitat_baselines.common.baseline_registry import baseline_registry

# 触发 __init__.py 里的注册
import vlnce_baselines 

def test_trainer():
    print("开始测试 ETPNav Trainer...")
    
    # 伪造一个极简的 Config
    mock_config = Config()
    mock_config.defrost()
    mock_config.TRAINER_NAME = "etpnav_trainer" # 指向我们刚才改的名字
    mock_config.CMD_TRAILING_OPTS = []
    
    # 获取被注册的 Trainer 类
    trainer_init = baseline_registry.get_trainer(mock_config.TRAINER_NAME)
    
    if trainer_init is None:
        print("❌ 找不到注册的 Trainer，检查 __init__.py 是否正确 import。")
        return
        
    print(f"✅ 成功找到 Trainer: {trainer_init.__name__}")
    
    # 尝试实例化
    try:
        # 这里我们只传 config 进去，看看它的 __init__ 会不会因为缺包报错
        trainer = trainer_init(mock_config)
        print("✅ Trainer 实例化成功！")
    except Exception as e:
        print("❌ Trainer 实例化失败，报错如下：")
        print(e)

if __name__ == "__main__":
    test_trainer()
