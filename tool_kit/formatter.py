import json
import os
from pathlib import Path
from collections import defaultdict

def process_json_files():
    """
    遍历所有JSON文件，将key改为递增序列，并收集video_id和category信息
    """
    base_path = Path(__file__).parent.parent  # PerceptionComp目录
    
    # 要处理的JSON文件列表
    json_files = [
        base_path / "winter_ques" /  "4in1_new.json",
    ]
    
    # 存储所有video_id和category
    video_ids = set()
    categories = defaultdict(int)
    all_items = []
    
    print("=" * 60)
    print("开始处理JSON文件...")
    print("=" * 60)
    
    # 遍历所有JSON文件
    for json_file in json_files:
        if not json_file.exists():
            print(f"⚠️  文件不存在: {json_file.name}")
            continue
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 确保data是列表
            if not isinstance(data, list):
                print(f"⚠️  {json_file.name} 不是数组格式")
                continue
            
            print(f"\n✓ 处理文件: {json_file.name}")
            print(f"  项目数量: {len(data)}")
            
            # 重新编号key并收集信息
            for idx, item in enumerate(data, 1):
                item['key'] = str(idx)  # 转换为字符串以保持原有格式
                
                # 收集video_id和category
                if 'video_id' in item:
                    video_ids.add(item['video_id'])
                if 'category' in item:
                    categories[item['category']] += 1
                
                all_items.append(item)
            
            # 保存修改后的文件
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"  ✓ 已保存修改")
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误 {json_file.name}: {e}")
        except Exception as e:
            print(f"❌ 处理错误 {json_file.name}: {e}")
    
    # 打印报告
    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)
    
    print(f"\n📊 统计信息:")
    print(f"  总项目数: {len(all_items)}")
    print(f"  不同的video_id数量: {len(video_ids)}")
    print(f"  不同的category数量: {len(categories)}")
    
    print(f"\n📹 所有video_id:")
    for video_id in sorted(video_ids):
        print(f"  - {video_id}")
    
    print(f"\n📂 category分布:")
    for category in sorted(categories.keys()):
        print(f"  - {category}: {categories[category]} 项")
    
    # 保存报告到文件
    report_file = base_path / "tool_kit" / "report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("JSON文件处理报告\n")
        f.write("=" * 60 + "\n\n")
        
        f.write(f"统计信息:\n")
        f.write(f"  总项目数: {len(all_items)}\n")
        f.write(f"  不同的video_id数量: {len(video_ids)}\n")
        f.write(f"  不同的category数量: {len(categories)}\n\n")
        
        f.write(f"所有video_id:\n")
        for video_id in sorted(video_ids):
            f.write(f"  - {video_id}\n")
        
        f.write(f"\ncategory分布:\n")
        for category in sorted(categories.keys()):
            f.write(f"  - {category}: {categories[category]} 项\n")
    
    print(f"\n✓ 报告已保存: report.txt")

if __name__ == "__main__":
    process_json_files()
