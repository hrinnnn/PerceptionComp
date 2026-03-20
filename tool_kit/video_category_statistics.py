#!/usr/bin/env python3
"""
Video category statistics tool.
Counts unique videos per category from JSON data (deduplicated by video_id).
"""

import json
import argparse
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, Set, List


def plot_donut_chart(
    category_videos: Dict[str, Set[str]],
    output_image: str,
    title: str = "video distribution"
):
    """Draw category statistics as a donut chart and save as an image."""
    if not category_videos:
        print("❌ No data available to plot")
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap, to_hex
    except ImportError:
        print("❌ Missing matplotlib. Please install it first: pip install matplotlib")
        return

    sorted_items = sorted(category_videos.items(), key=lambda x: len(x[1]), reverse=True)
    categories = [k for k, _ in sorted_items]
    counts = [len(v) for _, v in sorted_items]
    total = sum(counts)

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 8), dpi=150)

    # Build a smooth custom gradient from the provided reference colors,
    # then sample colors in order so neighboring slices look visually close.
    gradient_stops = [
        "#B5E1FF",  # Very light blue
        "#91C9FF",  # Sky blue
        "#C9D1F9",  # Light blue-violet
        "#C6A9D1",  # Soft lavender
        "#E2B6C3",  # Dusty rose
        "#E6B8D1",  # Gray pink
        "#F7BBD0",  # Sakura pink
        "#FFC2E0",  # Bright pink
    ]
    custom_cmap = LinearSegmentedColormap.from_list(
        "category_gradient",
        gradient_stops,
        N=max(len(categories), 256)
    )
    if len(categories) == 1:
        colors = [to_hex(custom_cmap(0.5))]
    else:
        colors = [
            to_hex(custom_cmap(i / (len(categories) - 1)))
            for i in range(len(categories))
        ]

    wedges, _, _ = ax.pie(
        counts,
        labels=None,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={'width': 0.42, 'edgecolor': 'white', 'linewidth': 2},
        autopct=lambda p: f"{p:.1f}%" if p >= 3 else "",
        pctdistance=0.80,
        textprops={'fontsize': 11, 'color': '#1f2937', 'fontweight': 'semibold'}
    )

    center_text = f"Total: {total}"
    ax.text(
        0,
        0,
        center_text,
        ha='center',
        va='center',
        fontsize=18,
        fontweight='bold',
        color='#111827'
    )

    legend_labels = [
        f"{cat}: {cnt} ({cnt / total * 100:.1f}%)"
        for cat, cnt in zip(categories, counts)
    ]
    ax.legend(
        wedges,
        legend_labels,
        title="Category and Count",
        loc='center left',
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        fontsize=10,
        title_fontsize=11
    )

    ax.set_title(title, fontsize=20, fontweight='bold', pad=20)
    ax.set_aspect('equal')
    plt.tight_layout()
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"✅ Donut chart saved to: {output_image}")


def load_json_file(file_path: str) -> list:
    """Load a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"❌ Failed to load file: {file_path}")
        print(f"   Error: {e}")
        return []


def collect_json_files(source_path: str) -> List[str]:
    """Collect all JSON file paths from a file or directory."""
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
    """Analyze one JSON file and return {category: {video_id_set}}."""
    data = load_json_file(file_path)
    category_videos = defaultdict(set)
    
    for item in data:
        if isinstance(item, dict):
            category = item.get('category', 'Unknown')
            video_id = item.get('video_id', 'Unknown')
            category_videos[category].add(video_id)
    
    return dict(category_videos)


def analyze_multiple_files(file_paths: List[str]) -> Dict[str, Set[str]]:
    """Analyze multiple JSON files and merge statistics."""
    category_videos = defaultdict(set)
    
    for file_path in file_paths:
        print(f"📖 Processing: {os.path.basename(file_path)}")
        data = load_json_file(file_path)
        
        for item in data:
            if isinstance(item, dict):
                category = item.get('category', 'Unknown')
                video_id = item.get('video_id', 'Unknown')
                category_videos[category].add(video_id)
    
    return dict(category_videos)


def print_statistics(category_videos: Dict[str, Set[str]], file_path: str = None):
    """Print statistics summary."""
    if not category_videos:
        print("❌ No data found")
        return
    
    print("\n" + "="*70)
    print("Video Category Statistics")
    print("="*70)
    
    if file_path:
        print(f"📁 File: {file_path}\n")
    
    # Sort by category name.
    sorted_categories = sorted(category_videos.items())
    total_categories = len(sorted_categories)
    total_videos = sum(len(videos) for _, videos in sorted_categories)
    
    print(f"{'Category':<20} {'Count':>10} {'Video List':<40}")
    print("-"*70)
    
    for category, videos in sorted_categories:
        video_count = len(videos)
        # If there are many videos, only show the first few.
        video_list = sorted(videos)
        if len(video_list) > 5:
            video_str = ", ".join(video_list[:5]) + "..."
        else:
            video_str = ", ".join(video_list)
        
        print(f"{category:<20} {video_count:>10} {video_str:<40}")
    
    print("-"*70)
    print(f"{'Total':<20} {total_videos:>10} ({total_categories} categories)")
    print("="*70 + "\n")


def save_statistics_to_file(category_videos: Dict[str, Set[str]], output_file: str):
    """Save statistics to a JSON file."""
    output_data = {}
    
    for category, videos in category_videos.items():
        output_data[category] = {
            "video_count": len(videos),
            "videos": sorted(list(videos))
        }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Statistics saved to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Count videos per category from JSON files"
    )
    parser.add_argument(
        'source',
        nargs='?',
        default='.',
        help='Path to a JSON file or directory (default: current directory)'
    )
    parser.add_argument(
        '-o', '--output',
        help='Save statistics output to a JSON file',
        default=None
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show full video ID lists'
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help='Generate a donut chart'
    )
    parser.add_argument(
        '--plot-output',
        default='video_category_donut.png',
        help='Donut chart output path (default: video_category_donut.png)'
    )
    parser.add_argument(
        '--plot-title',
        default='video distribution',
        help='Donut chart title'
    )
    
    args = parser.parse_args()
    
    # Collect JSON files.
    source_path = args.source if args.source != '.' else Path.cwd()
    json_files = collect_json_files(str(source_path))
    
    if not json_files:
        print(f"❌ No JSON files found: {args.source}")
        return
    
    print(f"✅ Found {len(json_files)} JSON file(s)\n")
    
    # Analyze files.
    if len(json_files) == 1:
        print(f"📖 Analyzing file: {json_files[0]}")
        category_videos = analyze_single_file(json_files[0])
        print_statistics(category_videos, json_files[0])
    else:
        category_videos = analyze_multiple_files(json_files)
        print("\n")
        print_statistics(category_videos)
    
    # Show detailed list.
    if args.verbose and category_videos:
        print("\nDetailed Video List:")
        print("="*70)
        for category in sorted(category_videos.keys()):
            videos = sorted(category_videos[category])
            print(f"\n[{category}] ({len(videos)} videos)")
            for i, video_id in enumerate(videos, 1):
                print(f"  {i:2d}. {video_id}")
    
    # Save to file.
    if args.output:
        save_statistics_to_file(category_videos, args.output)

    # Generate donut chart.
    if args.plot:
        plot_donut_chart(category_videos, args.plot_output, args.plot_title)


if __name__ == '__main__':
    main()
