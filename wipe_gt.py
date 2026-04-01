import json
import gzip
import os

def wipe_ground_truth(input_path, output_path):
    print(f"正在加载数据: {input_path} ...")
    
    # 1. 读取压缩的 JSON 数据
    with gzip.open(input_path, 'rt', encoding='utf-8') as f:
        data = json.load(f)
    
    # 兼容处理：检查数据是在 'episodes' 键下还是直接是一个列表
    episodes = data.get("episodes", data) if isinstance(data, dict) else data
    
    cleaned_episodes = []
    
    # 2. 遍历每一条导航任务
    for ep in episodes:
        clean_ep = ep.copy() # 复制一份，避免直接修改原内存
        
        # 3. 核心大扫除：移除所有可能泄露终点和路线的 key
        keys_to_remove = ["goals", "info", "reference_path", "trajectory"]
        for k in keys_to_remove:
            clean_ep.pop(k, None) # 如果有这个 key 就删掉，没有就不管
            
        cleaned_episodes.append(clean_ep)
    
    # 将清理后的 episodes 拼装回原格式，同时保留其他顶层数据（如 instruction_vocab）
    if isinstance(data, dict):
        cleaned_data = data.copy() # 先把原数据的壳子连同 vocab 一起复制过来
        cleaned_data["episodes"] = cleaned_episodes # 然后用清洗干净的 episodes 替换掉原来的
    else:
        cleaned_data = cleaned_episodes
        
    print(f"清理完成，共处理 {len(cleaned_episodes)} 条数据。正在保存...")
    
    # 4. 重新打包为 .gz 压缩文件给选手
    # 提示：不使用 indent 可以大幅减小最终文件的大小
    with gzip.open(output_path, 'wt', encoding='utf-8') as f:
        json.dump(cleaned_data, f)
        
    print(f"成功保存至: {output_path} \n")

# 假设你要处理的是 test 数据集，这里用 val_unseen 举例测试
# 在实际比赛中，把下面的路径换成你们真正的 test 数据集路径即可
if __name__ == "__main__":
    input_file = "Data/HA-R2R/val_unseen/val_unseen.json.gz"
    output_file = "Data/HA-R2R/val_unseen/val_unseen_participants.json.gz"
    
    if os.path.exists(input_file):
        wipe_ground_truth(input_file, output_file)
    else:
        print(f"找不到文件 {input_file}，请检查路径。")
