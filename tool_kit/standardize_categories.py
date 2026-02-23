"""
standardize_categories.py
--------------------------
Standardizes the "category" field across all JSON question files.

Mapping rules (added by zzx):
  sport / sports / Sports / Sport   → "sport"
  shopping / Shopping               → "shopping"
  outdoor tour / Outdoor tour / ... → "outdoor tour"
  shows / show / variety show / ... → "variety show"
  home tour / Home tour / ...       → "home tour"
"""

import json
import os
import glob
from pathlib import Path

# Root of the project (one level above tool_kit/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Files to process (relative to PROJECT_ROOT)
JSON_PATTERNS = [
    "winter_ques/**/*.json",
    "summer_ques/**/*.json",
]

# Canonical category mapping: lowercase stripped value → target
CATEGORY_MAP = {
    # sport variants
    "sport":        "sport",
    "sports":       "sport",
    # shopping variants
    "shopping":     "shopping",
    # outdoor tour variants
    "outdoor tour": "outdoor tour",
    "outdoor":      "outdoor tour",
    # variety show variants
    "variety show": "variety show",
    "variety shows":"variety show",
    "show":         "variety show",
    "shows":        "variety show",
    # home tour variants
    "home tour":    "home tour",
    "home":         "home tour",
}


def standardize(value: str) -> str:
    """Return the canonical category name, or the original if not in the map."""
    key = value.strip().lower()
    return CATEGORY_MAP.get(key, value)


def process_file(path: Path, dry_run: bool = False) -> dict:
    """Process a single JSON file. Returns a stats dict."""
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        return {"file": str(path.relative_to(PROJECT_ROOT)), "skipped": True, "reason": "empty file"}

    data = json.loads(raw)

    if not isinstance(data, list):
        return {"file": str(path.relative_to(PROJECT_ROOT)), "skipped": True, "reason": "not a list"}

    changed = 0
    before_counts: dict[str, int] = {}
    after_counts: dict[str, int] = {}

    for item in data:
        if "category" not in item:
            continue
        original = item["category"]
        canonical = standardize(original)
        before_counts[original] = before_counts.get(original, 0) + 1
        after_counts[canonical] = after_counts.get(canonical, 0) + 1
        if original != canonical:
            item["category"] = canonical
            changed += 1

    if not dry_run and changed > 0:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return {
        "file": str(path.relative_to(PROJECT_ROOT)),
        "changed": changed,
        "before": before_counts,
        "after": after_counts,
        "dry_run": dry_run,
    }


def main(dry_run: bool = False):
    all_json_files: list[Path] = []
    for pattern in JSON_PATTERNS:
        all_json_files.extend(PROJECT_ROOT.glob(pattern))

    all_json_files = sorted(set(all_json_files))

    print(f"Found {len(all_json_files)} JSON file(s) to process.\n")
    if dry_run:
        print("=== DRY RUN — no files will be written ===\n")

    total_changed = 0
    for path in all_json_files:
        stats = process_file(path, dry_run=dry_run)
        if stats.get("skipped"):
            print(f"[SKIP]  {stats['file']}  ({stats.get('reason', '')})")
            continue

        changed = stats["changed"]
        total_changed += changed
        status = "CHANGED" if changed else "OK    "
        print(f"[{status}]  {stats['file']}  ({changed} updated)")

        if changed:
            # Show what changed
            before = stats["before"]
            after  = stats["after"]
            all_keys = set(before) | set(after)
            for k in sorted(all_keys):
                b = before.get(k, 0)
                a = after.get(k, 0)
                if b != a:
                    canonical = standardize(k)
                    print(f"          \"{k}\" ({b}) → \"{canonical}\"")

    print(f"\nDone. Total entries updated: {total_changed}")
    if dry_run:
        print("(Dry run — no files modified.)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Standardize category fields in question JSON files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing to disk.",
    )
    args = parser.parse_args()
    main(dry_run=args.dry_run)
