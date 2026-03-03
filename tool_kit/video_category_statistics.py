#!/usr/bin/env python3
"""
视频分类统计工具
统计JSON文件中每个视频种类对应的视频数量（按video_id去重）
"""

import json
import argparse
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List


def load_json_file(file_path: str) -> list:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"❌ 加载文件失败: {file_path}")
        print(f"   错误: {e}")
        return []


def collect_json_files(source_path: str) -> List[str]:
    """收集JSON文件列表"""
    json_files = []
    
    if os.path.isfile(source_path):
        if source_path.endswith('.json'):
            json_files.append(source_path)
    elif os.path.isdir(source_path):
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(os.path.join(root, file))
    
    return sorted(json_files)


def analyze_single_file(file_path: str) -> Dict[str, Set[str]]:
    """分析单个JSON文件，返回 {category: {video_id集合}}"""
    data = load_json_file(file_path)
    category_videos = defaultdict(set)
    
    for item in data:
        if isinstance(item, dict):
            category = item.get('category', 'Unknown')
            video_id = item.get('video_id', 'Unknown')
            category_videos[category].add(video_id)
    
    return dict(category_videos)


def analyze_multiple_files(file_paths: List[str]) -> Dict[str, Set[str]]:
    """分析多个JSON文件，合并统计结果"""
    category_videos = defaultdict(set)
    
    for file_path in file_paths:
        print(f"📖 处理: {os.path.basename(file_path)}")
        data = load_json_file(file_path)
        
        for item in data:
            if isinstance(item, dict):
                category = item.get('category', 'Unknown')
                video_id = item.get('video_id', 'Unknown')
                category_videos[category].add(video_id)
    
    return dict(category_videos)


def print_statistics(category_videos: Dict[str, Set[str]], file_path: str = None):
    """打印统计结果"""
    if not category_videos:
        print("❌ 没有找到数据")
        return
    
    print("\n" + "="*70)
    print("视频分类统计结果")
    print("="*70)
    
    if file_path:
        print(f"📁 文件: {file_path}\n")
    
    # 按分类排序
    sorted_categories = sorted(category_videos.items())
    total_categories = len(sorted_categories)
    total_videos = sum(len(videos) for _, videos in sorted_categories)
    
    print(f"{'分类':<20} {'视频数量':>10} {'视频列表':<40}")
    print("-"*70)
    
    for category, videos in sorted_categories:
        video_count = len(videos)
        # 如果视频较多，只显示前几个
        video_list = sorted(videos)
        if len(video_list) > 5:
            video_str = ", ".join(video_list[:5]) + "..."
        else:
            video_str = ", ".join(video_list)
        
        print(f"{category:<20} {video_count:>10} {video_str:<40}")
    
    print("-"*70)
    print(f"{'总计':<20} {total_videos:>10} (共 {total_categories} 个分类)")
    print("="*70 + "\n")


def save_statistics_to_file(category_videos: Dict[str, Set[str]], output_file: str):
    """将统计结果保存为JSON文件"""
    output_data = {}
    
    for category, videos in category_videos.items():
        output_data[category] = {
            "video_count": len(videos),
            "videos": sorted(list(videos))
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 统计结果已保存到: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="统计JSON文件中每个视频分类对应的视频数量"
    )
    parser.add_argument(
        'source',
        nargs='?',
        default='.',
        help='JSON文件或目录路径 (默认: 当前目录)'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出结果到JSON文件',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细的视频列表'
    )
    
    args = parser.parse_args()
    
    # 收集JSON文件
    source_path = args.source if args.source != '.' else Path.cwd()
    json_files = collect_json_files(str(source_path))
    
    if not json_files:
        print(f"❌ 未找到JSON文件: {args.source}")
        return
    
    print(f"✅ 找到 {len(json_files)} 个JSON文件\n")
    
    # 分析文件
    if len(json_files) == 1:
        print(f"📖 分析文件: {json_files[0]}")
        category_videos = analyze_single_file(json_files[0])
        print_statistics(category_videos, json_files[0])
    else:
        category_videos = analyze_multiple_files(json_files)
        print("\n")
        print_statistics(category_videos)
    
    # 显示详细列表
    if args.verbose and category_videos:
        print("\n详细视频列表:")
        print("="*70)
        for category in sorted(category_videos.keys()):
            videos = sorted(category_videos[category])
            print(f"\n【{category}】({len(videos)} 个视频)")
            for i, video_id in enumerate(videos, 1):
                print(f"  {i:2d}. {video_id}")
    
    # 保存到文件
    if args.output:
        save_statistics_to_file(category_videos, args.output)


if __name__ == '__main__':
    main()
