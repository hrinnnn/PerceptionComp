import argparse
import json
import os
from collections import defaultdict
from typing import Dict, List


ABILITY_LABELS = [
    "Semantic understanding",
    "Spatial understanding",
    "Temporal understanding",
    "Correspondence",
    "Visual knowledge",
    "World modeling",
]

ABILITY_SET = set(ABILITY_LABELS)


def normalize_ability(label: str) -> str:
    label = (label or "").strip()
    if label in ABILITY_SET:
        return label

    lower = label.lower()
    alias_map = {
        "semantic": "Semantic understanding",
        "semantic understanding": "Semantic understanding",
        "spatial": "Spatial understanding",
        "spatial understanding": "Spatial understanding",
        "temporal": "Temporal understanding",
        "temporal understanding": "Temporal understanding",
        "correspondence": "Correspondence",
        "visual knowledge": "Visual knowledge",
        "world modeling": "World modeling",
        "world model": "World modeling",
    }
    if lower in alias_map:
        return alias_map[lower]

    for canonical in ABILITY_LABELS:
        if canonical.lower() in lower:
            return canonical

    return ""


def normalize_step_abilities(step: Dict) -> List[str]:
    raw_abilities = step.get("abilities")
    candidates: List[str] = []

    if isinstance(raw_abilities, list):
        candidates.extend(str(v) for v in raw_abilities)
    elif isinstance(raw_abilities, str):
        candidates.append(raw_abilities)

    # Backward compatibility with historical single-label schema.
    if "ability" in step:
        candidates.append(str(step.get("ability", "")))

    normalized: List[str] = []
    seen = set()
    for c in candidates:
        ability = normalize_ability(c)
        if ability and ability not in seen:
            normalized.append(ability)
            seen.add(ability)

    return normalized


def build_statistics(records: List[Dict]) -> Dict:
    counts = defaultdict(int)
    total_steps = 0
    total_ability_assignments = 0

    for rec in records:
        step_items = rec.get("step_abilities", [])
        if not isinstance(step_items, list):
            continue

        for step in step_items:
            if not isinstance(step, dict):
                continue

            abilities = normalize_step_abilities(step)
            if not abilities:
                continue

            total_steps += 1
            total_ability_assignments += len(abilities)
            for ability in abilities:
                counts[ability] += 1

    stats = {}
    for ability in ABILITY_LABELS:
        c = counts[ability]
        pct = (c / total_steps * 100.0) if total_steps > 0 else 0.0
        stats[ability] = {
            "count": c,
            "percentage": round(pct, 2),
        }

    return {
        "total_questions": len(records),
        "total_steps": total_steps,
        "total_ability_assignments": total_ability_assignments,
        "abilities": stats,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recompute step ability statistics directly from step_ability_results.json"
    )
    parser.add_argument(
        "--input_json",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result/step_ability_results.json",
        type=str,
        help="Path to step_ability_results.json",
    )
    parser.add_argument(
        "--output_json",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result/step_ability_stats.json",
        type=str,
        help="Path to output step_ability_stats.json",
    )

    args = parser.parse_args()

    with open(args.input_json, "r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list):
        raise ValueError("Input JSON must be a list")

    stats = build_statistics(records)

    output_dir = os.path.dirname(args.output_json)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print(f"Done. Wrote stats to: {args.output_json}")
    print(f"Total questions: {stats['total_questions']}")
    print(f"Total steps: {stats['total_steps']}")
    print(f"Total ability assignments: {stats['total_ability_assignments']}")


if __name__ == "__main__":
    main()
