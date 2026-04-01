import gzip
import json

def get_unique_scenes(file_path):
    print(f"正在扫描: {file_path} ...")
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            data = json.load(f)
        
        # 兼容处理提取 episodes 列表
        episodes = data.get("episodes", data) if isinstance(data, dict) else data
        
        scenes = set()
        for ep in episodes:
            if "scene_id" in ep:
                # 原始 scene_id 格式例如 "mp3d/7y3sRwLe3Va/7y3sRwLe3Va.glb"
                # 我们直接截取中间的建筑哈希值 "7y3sRwLe3Va" 会更直观
                raw_id = ep["scene_id"]
                building_id = raw_id.split('/')[1] if '/' in raw_id else raw_id
                scenes.add(building_id)
                
        return scenes
    except Exception as e:
        print(f"  [!] 读取失败: {e}")
        return set()

if __name__ == "__main__":
    # 定义文件路径
    train_file = "Data/HA-R2R/train/train.json.gz"
    val_seen_file = "Data/HA-R2R/val_seen/val_seen.json.gz"
    val_unseen_file = "Data/HA-R2R/val_unseen/val_unseen.json.gz"

    # 获取各自的场景集合
    train_scenes = get_unique_scenes(train_file)
    val_seen_scenes = get_unique_scenes(val_seen_file)
    val_unseen_scenes = get_unique_scenes(val_unseen_file)

    # 打印统计结果
    print("\n" + "="*40)
    print("📊 数据集场景 (Scene) 统计结果")
    print("="*40)
    
    print(f"Train      涵盖建筑数: {len(train_scenes)}")
    print(f"Val_seen   涵盖建筑数: {len(val_seen_scenes)}")
    print(f"Val_unseen 涵盖建筑数: {len(val_unseen_scenes)}\n")

    # 验证逻辑：计算交集
    print("🔍 过拟合验证逻辑分析：")
    
    # 1. Train vs Val_seen
    seen_intersect = train_scenes.intersection(val_seen_scenes)
    print(f"➤ Train 与 Val_seen 重合的建筑数量: {len(seen_intersect)}")
    if len(seen_intersect) == len(val_seen_scenes):
        print("  ✅ 结论: Val_seen 的环境是模型见过的 (用来测试模型能不能在熟练的地图里听懂新指令)。")
    else:
        print("  ⚠️ 警告: Val_seen 有部分地图模型没见过！")

    print("-" * 40)
    
    # 2. Train vs Val_unseen
    unseen_intersect = train_scenes.intersection(val_unseen_scenes)
    print(f"➤ Train 与 Val_unseen 重合的建筑数量: {len(unseen_intersect)}")
    if len(unseen_intersect) == 0:
        print("  ✅ 结论: 0 重合！Val_unseen 里的建筑对模型来说是 100% 陌生的，用来测试真正的泛化能力！")
    else:
        print(f"  ⚠️ 警告: 存在 {len(unseen_intersect)} 个泄露的建筑！")