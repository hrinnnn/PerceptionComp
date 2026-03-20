#!/usr/bin/env python3
"""
Model ability distribution visualization.
Draws a donut chart showing the distribution of model abilities in benchmark questions.
"""

import json
import argparse
from collections import OrderedDict
from typing import Dict


def plot_ability_distribution(
    abilities: Dict[str, int],
    total_steps: int,
    output_image: str = "model_ability_distribution.png",
    title: str = "Model Ability Distribution by Total Steps"
):
    """Draw ability distribution as a bar chart and save as an image."""
    if not abilities:
        print("❌ No data available to plot")
        return

    if total_steps <= 0:
        print("❌ total_steps must be a positive integer")
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap, to_hex
    except ImportError:
        print("❌ Missing matplotlib. Please install it first: pip install matplotlib")
        return

    # Sort by count descending
    sorted_items = sorted(abilities.items(), key=lambda x: x[1], reverse=True)
    categories = [k for k, _ in sorted_items]
    counts = [v for _, v in sorted_items]
    percentages = [(count / total_steps) * 100 for count in counts]

    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 8), dpi=150)

    # Build gradient from reference colors (matching video_category_statistics.py)
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
        "ability_gradient",
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

    bars = ax.barh(
        categories,
        percentages,
        color=colors,
        edgecolor='white',
        linewidth=1.2,
        height=0.65
    )
    ax.invert_yaxis()

    max_pct = max(percentages) if percentages else 0
    x_limit = max(100, max_pct * 1.2)
    ax.set_xlim(0, x_limit)

    for bar, count, pct in zip(bars, counts, percentages):
        ax.text(
            bar.get_width() + x_limit * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{pct:.2f}% ({count})",
            va='center',
            ha='left',
            fontsize=10,
            color='#1f2937',
            fontweight='semibold'
        )

    summary_text = (
        f"total_steps: {total_steps}\n"
        f"ability_assignments: {sum(counts)}"
    )
    ax.text(
        0.98,
        0.03,
        summary_text,
        transform=ax.transAxes,
        ha='right',
        va='bottom',
        fontsize=10,
        color='#374151',
        bbox={
            'boxstyle': 'round,pad=0.4',
            'facecolor': 'white',
            'edgecolor': '#d1d5db',
            'alpha': 0.9
        }
    )

    ax.set_title(title, fontsize=20, fontweight='bold', pad=20)
    ax.set_xlabel('Percentage of total_steps (%)', fontsize=12, color='#111827')
    ax.set_ylabel('Ability Type', fontsize=12, color='#111827')
    ax.xaxis.grid(True, linestyle='--', alpha=0.35)
    ax.yaxis.grid(False)
    plt.tight_layout()
    plt.savefig(output_image, dpi=300, bbox_inches='tight')
    plt.close(fig)

    print(f"✅ Bar chart saved to: {output_image}")


def main():
    parser = argparse.ArgumentParser(
        description="Visualize model ability distribution as a bar chart"
    )
    parser.add_argument(
        '-o', '--output',
        default='model_ability_distribution.png',
        help='Output image path (default: model_ability_distribution.png)'
    )
    parser.add_argument(
        '-t', '--title',
        default='Model Ability Distribution by Total Steps',
        help='Chart title'
    )
    parser.add_argument(
        '-j', '--json',
        help='Load abilities from a JSON file (must have "abilities" key with name->count mapping)'
    )
    parser.add_argument(
        '--total-steps',
        type=int,
        default=None,
        help='Override total_steps denominator for percentage calculation'
    )
    
    args = parser.parse_args()
    
    # Default benchmark data
    abilities = OrderedDict([
        ("Temporal understanding", 4331),
        ("Semantic understanding", 3606),
        ("Spatial understanding", 3141),
        ("Correspondence", 1259),
        ("World modeling", 963),
        ("Visual knowledge", 899),
    ])
    total_steps = 4395
    
    # Load from JSON if provided
    if args.json:
        try:
            with open(args.json, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'abilities' in data:
                # Handle both {name: count} and {name: {count: int, percentage: float}} formats
                abilities = OrderedDict()
                for name, value in data['abilities'].items():
                    if isinstance(value, dict):
                        abilities[name] = value.get('count', 0)
                    else:
                        abilities[name] = value

            if 'total_steps' in data and isinstance(data['total_steps'], int):
                total_steps = data['total_steps']
        except Exception as e:
            print(f"⚠️  Failed to load JSON file: {e}")
            print("📖 Using default benchmark data instead")

    if args.total_steps is not None:
        total_steps = args.total_steps
    
    print("📊 Model Ability Distribution")
    print("="*70)
    total_assignments = sum(abilities.values())
    for ability, count in abilities.items():
        percentage = (count / total_steps * 100) if total_steps > 0 else 0
        print(f"  {ability:<30} {count:>6} ({percentage:>6.2f}% of total_steps)")
    print("="*70)
    print(f"  {'Total Steps':<30} {total_steps:>6}")
    print(f"  {'Ability Assignments':<30} {total_assignments:>6}")
    print("="*70 + "\n")
    
    plot_ability_distribution(abilities, total_steps, args.output, args.title)


if __name__ == '__main__':
    main()
