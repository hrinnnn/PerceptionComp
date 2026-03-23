#!/usr/bin/env python3
"""
YouTube视频下载和截取脚本
使用方法: python youtube_downloader.py <config.json>
或从当前目录读取 video_config.json
"""

import os
import subprocess
import sys
import json
from pathlib import Path
import tempfile


def parse_time(time_str):
    """将时间字符串转换为秒数。支持格式: '1m30s', '5m', '30s'"""
    total_seconds = 0
    parts = time_str.replace('m', ' m').replace('s', ' s').split()
    
    for i in range(0, len(parts), 2):
        if i + 1 < len(parts):
            value = int(parts[i])
            unit = parts[i + 1]
            if unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value
    
    return total_seconds


def parse_time_range(range_str):
    """解析时间范围字符串。例如: '0m~4m' -> (0, 240)"""
    start, end = range_str.split('~')
    start_seconds = parse_time(start.strip())
    end_seconds = parse_time(end.strip())
    return start_seconds, end_seconds


def download_video(url, output_path):
    """使用yt-dlp下载视频"""
    print(f"正在下载视频: {url}")
    try:
        subprocess.run([
            'yt-dlp',
            '-f', 'best',
            '-o', output_path,
            url
        ], check=True)
        print(f"✓ 视频下载完成: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 下载失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ 错误: 未找到 yt-dlp，请先安装: pip install yt-dlp")
        return False


def cut_video(input_path, output_path, start_time, end_time):
    """使用ffmpeg截取视频的指定时间段"""
    duration = end_time - start_time
    
    print(f"  截取: {start_time}s - {end_time}s (时长: {duration}s)")
    try:
        subprocess.run([
            'ffmpeg',
            '-i', input_path,
            '-ss', str(start_time),
            '-to', str(end_time),
            '-c', 'copy',  # 不重新编码，速度更快
            '-y',  # 覆盖输出文件
            output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"  ✓ 保存: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ 截取失败: {e}")
        return False
    except FileNotFoundError:
        print("✗ 错误: 未找到 ffmpeg，请先安装: brew install ffmpeg (macOS) 或 apt-get install ffmpeg (Linux)")
        return False


def load_config(config_path):
    """从JSON配置文件加载视频信息"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not isinstance(config, dict) or 'videos' not in config:
            print("✗ 配置文件格式错误: 必须包含 'videos' 字段")
            sys.exit(1)
        
        if not isinstance(config['videos'], list) or len(config['videos']) == 0:
            print("✗ 配置文件中没有视频条目")
            sys.exit(1)
        
        return config['videos']
    except FileNotFoundError:
        print(f"✗ 配置文件不存在: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ 配置文件JSON格式错误: {e}")
        sys.exit(1)


def main():
    """主函数 - 从配置文件读取视频信息"""
    # 设置输出文件夹
    videos_dir = Path(__file__).parent.parent / 'videos'
    videos_dir.mkdir(exist_ok=True)
    
    # 确定配置文件路径
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        # 默认查找 tool_kit 目录下的 video_config.json
        config_path = Path(__file__).parent / 'video_config.json'
        if not config_path.exists():
            print("✗ 找不到配置文件")
            print(f"请在 {config_path} 创建配置文件")
            print("\n配置文件格式示例:")
            print(json.dumps({
                "videos": [
                    {
                        "url": "https://www.youtube.com/watch?v=...",
                        "name": "video_name",
                        "time_ranges": ["0m~4m", "4m~8m"]
                    }
                ]
            }, indent=2, ensure_ascii=False))
            sys.exit(1)
    
    print("=" * 60)
    print("YouTube 视频下载和截取工具 (从配置文件读取)")
    print("=" * 60)
    
    # 加载配置
    videos = load_config(config_path)
    
    print(f"\n找到 {len(videos)} 个视频条目")
    
    # 处理每个视频
    for video_idx, video_info in enumerate(videos, 1):
        print("\n" + "=" * 60)
        print(f"[{video_idx}/{len(videos)}] 处理视频")
        print("=" * 60)
        
        # 验证必要字段
        try:
            url = video_info.get('url', '').strip()
            video_name = video_info.get('name', '').strip()
            time_ranges = video_info.get('time_ranges', [])
            
            if not url:
                print("✗ 错误: 缺少 'url' 字段")
                continue
            if not video_name:
                print("✗ 错误: 缺少 'name' 字段")
                continue
            if not time_ranges or not isinstance(time_ranges, list):
                print("✗ 错误: 'time_ranges' 必须是非空列表")
                continue
            
            print(f"视频名称: {video_name}")
            print(f"URL: {url}")
            print(f"时间段数: {len(time_ranges)}")
        except Exception as e:
            print(f"✗ 配置读取错误: {e}")
            continue
        
        # 解析时间段
        try:
            parsed_ranges = []
            for r in time_ranges:
                start, end = parse_time_range(r)
                parsed_ranges.append((start, end, r))
        except Exception as e:
            print(f"✗ 时间段格式错误: {e}")
            continue
        
        # 临时文件夹存储原始视频
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_video = os.path.join(temp_dir, 'temp_video.mp4')
            
            # 下载视频
            if not download_video(url, temp_video):
                continue
            
            # 检查视频文件是否存在
            if not os.path.exists(temp_video):
                print("✗ 下载的视频文件不存在")
                continue
            
            # 截取和保存各个时间段
            print(f"\n开始截取视频段:")
            for i, (start, end, range_str) in enumerate(parsed_ranges, 1):
                # 生成输出文件名
                start_min = start // 60
                end_min = end // 60
                output_filename = f"{video_name}_{start_min}-{end_min}.mp4"
                output_path = videos_dir / output_filename
                
                print(f"\n[{i}/{len(parsed_ranges)}] {range_str}")
                cut_video(temp_video, str(output_path), start, end)
    
    print("\n" + "=" * 60)
    print(f"✓ 所有视频段已保存到: {videos_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
