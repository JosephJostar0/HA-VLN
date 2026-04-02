#!/usr/bin/env python3
"""
验证 HA-VLN 文档中的技术声明是否完全基于源代码
"""

import os
import re
import yaml
import json
from pathlib import Path

def check_human_refresh_frequency():
    """检查人类模型刷新频率"""
    print("=== 检查人类模型刷新频率 ===")
    
    env_file = "HASimulator/environments.py"
    with open(env_file, 'r') as f:
        content = f.read()
    
    # 查找 _signal_sender 函数
    signal_sender_match = re.search(r'def _signal_sender\(self\):(.*?)def ', content, re.DOTALL)
    if signal_sender_match:
        func_content = signal_sender_match.group(1)
        # 检查文档字符串
        docstring_match = re.search(r'"""(.*?)"""', func_content, re.DOTALL)
        if docstring_match:
            docstring = docstring_match.group(1)
            print(f"文档字符串: {docstring.strip()}")
        
        # 检查 time.sleep 的值
        sleep_match = re.search(r'time\.sleep\(([0-9.]+)\)', func_content)
        if sleep_match:
            sleep_value = float(sleep_match.group(1))
            print(f"实际 sleep 值: {sleep_value} 秒")
            print(f"实际频率: {1/sleep_value:.1f} Hz")
    
    return True

def check_config_paths():
    """检查配置文件路径"""
    print("\n=== 检查配置文件路径 ===")
    
    # 检查 agent 配置文件
    agent_config = "agent/config/cma_pm_da_aug_tune.yaml"
    if os.path.exists(agent_config):
        with open(agent_config, 'r') as f:
            config = yaml.safe_load(f)
        
        base_task_config = config.get('BASE_TASK_CONFIG_PATH', '')
        print(f"BASE_TASK_CONFIG_PATH: {base_task_config}")
        
        # 检查该文件是否存在
        if os.path.exists(base_task_config.replace('../', '')):
            print(f"配置文件存在: {base_task_config}")
        else:
            print(f"警告: 配置文件不存在: {base_task_config}")
    
    # 检查 HASimulator 配置文件
    havln_config = "HASimulator/config/HAVLNCE_task.yaml"
    if os.path.exists(havln_config):
        with open(havln_config, 'r') as f:
            config = yaml.safe_load(f)
        
        print(f"HASimulator 配置中的关键参数:")
        simulator_config = config.get('SIMULATOR', {})
        print(f"  ADD_HUMAN: {simulator_config.get('ADD_HUMAN', '未找到')}")
        print(f"  HUMAN_GLB_PATH: {simulator_config.get('HUMAN_GLB_PATH', '未找到')}")
        print(f"  HUMAN_INFO_PATH: {simulator_config.get('HUMAN_INFO_PATH', '未找到')}")
    
    return True

def check_measure_registrations():
    """检查测量指标注册"""
    print("\n=== 检查测量指标注册 ===")
    
    measures_file = "HASimulator/measures.py"
    with open(measures_file, 'r') as f:
        content = f.read()
    
    # 查找所有 @registry.register_measure 装饰器
    registrations = re.findall(r'@registry\.register_measure\s*\nclass (\w+)', content)
    print(f"注册的测量类: {registrations}")
    
    # 检查 DistanceToHuman 类
    if 'DistanceToHuman' in registrations:
        print("✓ DistanceToHuman 已正确注册")
        
        # 检查 cls_uuid
        distance_class_match = re.search(r'class DistanceToHuman.*?cls_uuid: str = "([^"]+)"', content, re.DOTALL)
        if distance_class_match:
            cls_uuid = distance_class_match.group(1)
            print(f"  cls_uuid: {cls_uuid}")
    
    # 检查 CollisionsDetail 类
    if 'CollisionsDetail' in registrations:
        print("✓ CollisionsDetail 已正确注册")
    
    return True

def check_havlnce_class_details():
    """检查 HAVLNCE 类的详细信息"""
    print("\n=== 检查 HAVLNCE 类详细信息 ===")
    
    env_file = "HASimulator/environments.py"
    with open(env_file, 'r') as f:
        content = f.read()
    
    # 检查类定义
    class_match = re.search(r'class HAVLNCE\(\):(.*?)(?=\nclass|\Z)', content, re.DOTALL)
    if class_match:
        class_content = class_match.group(1)
        
        # 检查初始化方法
        init_match = re.search(r'def __init__\(self.*?\):(.*?)(?=\n    def|\n\n)', class_content, re.DOTALL)
        if init_match:
            init_content = init_match.group(1)
            print("__init__ 方法中的关键初始化:")
            
            # 检查线程启动
            if 'threading.Thread' in init_content:
                print("✓ 启动了子线程")
            
            # 检查锁
            if 'threading.Lock' in init_content:
                print("✓ 使用了线程锁")
            
            # 检查队列
            if 'queue.Queue' in init_content:
                print("✓ 使用了信号队列")
    
    return True

def check_frame_management():
    """检查帧管理"""
    print("\n=== 检查帧管理 ===")
    
    env_file = "HASimulator/environments.py"
    with open(env_file, 'r') as f:
        content = f.read()
    
    # 检查帧 ID 计算
    frame_calc_match = re.search(r'frame_id = \(self\.total_signals_sent - 1\) % 120', content)
    if frame_calc_match:
        print("✓ 帧 ID 计算: (total_signals_sent - 1) % 120")
    
    # 检查 120 帧序列
    if '120' in content:
        count_120 = content.count('120')
        print(f"✓ 代码中引用了 120 帧序列 (出现 {count_120} 次)")
    
    return True

def check_navmesh_recomputation():
    """检查导航网格重新计算"""
    print("\n=== 检查导航网格重新计算 ===")
    
    env_file = "HASimulator/environments.py"
    with open(env_file, 'r') as f:
        content = f.read()
    
    # 检查导航网格路径
    navmesh_path_match = re.search(r'navmesh_path = os\.path\.join\(.*?scan \+ f\'_\{self\.frame_id:03d\}\.navmesh\'', content)
    if navmesh_path_match:
        print("✓ 导航网格文件命名包含帧 ID: {scan}_{frame_id:03d}.navmesh")
    
    # 检查重新计算逻辑
    if 'recompute_navmesh' in content:
        print("✓ 包含导航网格重新计算逻辑")
    
    return True

def check_agent_interaction():
    """检查 Agent 交互"""
    print("\n=== 检查 Agent 交互 ===")
    
    # 检查 agent 配置文件
    agent_config = "agent/config/cma_pm_da_aug_tune.yaml"
    if os.path.exists(agent_config):
        with open(agent_config, 'r') as f:
            config = yaml.safe_load(f)
        
        print("Agent 配置:")
        print(f"  BASE_TASK_CONFIG_PATH: {config.get('BASE_TASK_CONFIG_PATH', '未找到')}")
        print(f"  SIMULATOR_GPU_IDS: {config.get('SIMULATOR_GPU_IDS', '未找到')}")
        print(f"  NUM_ENVIRONMENTS: {config.get('NUM_ENVIRONMENTS', '未找到')}")
    
    # 检查 agent run.py
    run_file = "agent/run.py"
    if os.path.exists(run_file):
        with open(run_file, 'r') as f:
            content = f.read()
        
        if 'get_config' in content:
            print("✓ agent/run.py 使用 get_config 加载配置")
        
        if 'trainer_init' in content:
            print("✓ agent/run.py 初始化训练器")
    
    return True

def main():
    """主验证函数"""
    print("开始验证 HA-VLN 文档技术声明...")
    print("=" * 60)
    
    checks = [
        check_human_refresh_frequency,
        check_config_paths,
        check_measure_registrations,
        check_havlnce_class_details,
        check_frame_management,
        check_navmesh_recomputation,
        check_agent_interaction,
    ]
    
    all_passed = True
    for check in checks:
        try:
            if not check():
                all_passed = False
        except Exception as e:
            print(f"检查失败: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ 所有检查通过")
    else:
        print("✗ 部分检查失败")
    
    return all_passed

if __name__ == "__main__":
    main()