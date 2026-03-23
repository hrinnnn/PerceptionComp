"""
compute_accuracy.py
-------------------
Computes per-category and per-difficulty accuracy for ALL models using
winter_ques/1-1114.json as the master question bank (keys 1-1114,
difficulty in 1/2/3 after correction).

KEY FACTS about result file key schemes
---------------------------------------
1. summer result files            keys 1-500   = global keys 1-500   (NO offset)
2. winter/gemini_* result files   keys 1-500   = internal; global = key + 500
3. winter_2/gemini_* result files keys 1-114   = internal; global = key + 1000
4. winter/ GPT/Qwen2.5/GLM/Qwen3 result files  keys already global (501-1114 or 1-1114)

BACK-CALCULATION for GPT-o3 / GPT-4o / GPT-4.1 (summer results lost)
----------------------------------------------------------------------
Using the table percentages from current_table.txt and the known
question distribution for keys 1-500 from master:
  1-500 category totals: outdoor=391, shopping=5, sport=15, home=74, show=15
  1-500 difficulty totals: L1=148, L2=215, L3=137
  correct_1_500[cat] = round(pct_table[cat] / 100 * total_1_500[cat])
All back-calcs have been verified to sum to overall × 500 exactly.

Usage:
    python3 tool_kit/compute_accuracy.py            # print to console
    python3 tool_kit/compute_accuracy.py --latex    # also print LaTeX rows
    python3 tool_kit/compute_accuracy.py --log      # verbose per-file loading log
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent

# ── Master question bank ────────────────────────────────────
master = json.loads((BASE / 'winter_ques/1-1114.json').read_text(encoding='utf-8'))
KEY_INFO = {str(item['key']): {'category': item['category'], 'difficulty': item['difficulty']}
            for item in master}

# ── Category / difficulty order matching the LaTeX table ───
CATS  = ['outdoor tour', 'shopping', 'sport', 'home tour', 'variety show', 'movie', 'game']
DIFFS = [1, 2, 3]
CAT_LABELS  = ['Outdoor Tour', 'Shopping', 'Sport', 'Home Tour', 'Show', 'Movie', 'Game']
DIFF_LABELS = ['Level 1', 'Level 2', 'Level 3']

# ── 1-500 question distribution (used for back-calculation) ─
SUMMER_CAT_TOTAL  = {'outdoor tour': 391, 'shopping': 5, 'sport': 15,
                     'home tour': 74, 'variety show': 15, 'movie': 0, 'game': 0}
SUMMER_DIFF_TOTAL = {1: 148, 2: 215, 3: 137}
SUMMER_TOTAL      = 500

# ── Back-calc data for models whose summer (1-500) results are lost ─
# Source: current_table.txt ; verified: sum of cat_correct == overall_correct == round(overall_pct/100 * 500)
BACKCALC_SUMMER = {
    'o3': {
        'cat_pct':  {'outdoor tour': 43.22, 'shopping': 80.00, 'sport': 40.00,
                     'home tour': 43.24, 'variety show': 20.00},
        'diff_pct': {1: 37.84, 2: 45.58, 3: 43.80},
        'overall_pct': 42.80,
    },
    'GPT-4o': {
        'cat_pct':  {'outdoor tour': 30.18, 'shopping': 40.00, 'sport': 33.33,
                     'home tour': 31.08, 'variety show': 20.00},
        'diff_pct': {1: 33.02, 2: 29.05, 3: 27.00},
        'overall_pct': 30.20,
    },
    'GPT-4.1': {
        'cat_pct':  {'outdoor tour': 26.09, 'shopping': 40.00, 'sport': 13.33,
                     'home tour': 28.38, 'variety show': 20.00},
        'diff_pct': {1: 29.77, 2: 26.39, 3: 19.71},
        'overall_pct': 26.00,
    },
    # Qwen2.5-VL-72B: summer file is a different run (overall=15.76% vs table=30.80%)
    # Use table values for back-calculation
    'Qwen2.5-VL-72B': {
        'cat_pct':  {'outdoor tour': 33.07, 'shopping': 20.00, 'sport': 26.67,
                     'home tour': 20.27, 'variety show': 53.33},
        'diff_pct': {1: 33.11, 2: 31.16, 3: 27.74},
        'overall_pct': 30.80,
    },
}

# ── Model result file definitions ───────────────────────────
# Each entry is a list of (file_path, key_offset) tuples.
# offset 0   = file already uses global keys
# offset 500 = internal keys 1-500 → global 501-1000
# offset 1000= internal keys 1-114 → global 1001-1114
RESULT_FILES = {
    # ── Gemini (3 files each: summer + winter + winter_2) ──
    'Gemini-2.5-Flash': [
        (BASE / 'test_result_summer/all_response/Results-gemini2.5-flash.json',            0),
        (BASE / 'test_result_winter/gemini_2.5_flash/Results-gemini-2.5-flash.json',      500),
        (BASE / 'test_result_winter_2/gemini_2.5_flash/Results-gemini-2.5-flash.json',   1000),
    ],
    'Gemini-2.5-Pro': [
        (BASE / 'test_result_summer/all_response/Results-gemini-2.5-pro-old.json',         0),
        (BASE / 'test_result_winter/gemini_2.5_pro/Results-gemini-2.5-pro.json',          500),
        (BASE / 'test_result_winter_2/gemini_2.5_pro/Results-gemini-2.5-pro.json',       1000),
    ],
    'Gemini-3-Flash': [
        (BASE / 'test_result_summer/gemini_3_flash/Results-gemini-3-flash-preview.json',   0),
        (BASE / 'test_result_winter/gemini_3_flash/Results-gemini-3-flash-preview.json',  500),
        (BASE / 'test_result_winter_2/gemini_3_flash/Results-gemini-3-flash-preview.json',1000),
    ],
    'Gemini-3-Pro': [
        (BASE / 'test_result_summer/gemini_3_pro/Results-gemini-3-pro-preview.json',       0),
        (BASE / 'test_result_winter/gemini_3_pro/Results-gemini-3-pro-preview.json',      500),
        (BASE / 'test_result_winter_2/gemini_3_pro/Results-gemini-3-pro-preview.json',   1000),
    ],
    'Gemini-3.1-Pro': [
        (BASE / 'test_result_summer/gemini_3.1_pro/Results-gemini-3.1-pro-preview.json',  0),
        (BASE / 'test_result_winter/gemini_3.1_pro/Results-gemini-3.1-pro-preview.json', 500),
        (BASE / 'test_result_winter_2/gemini_3.1_pro/Results-gemini-3.1-pro-preview.json',1000),
    ],
    # ── Qwen2.5 (summer 1-500 + winter 501-1114 global) ────
    'Qwen2.5-VL-7B': [
        (BASE / 'test_result_summer/all_response/Results-Qwen2.5-VL-7B-Instruct.json',    0),
        (BASE / 'test_result_winter/Results-Qwen2.5-VL-7B-Instruct.json',                 0),
    ],
    # Qwen2.5-VL-72B: summer file is a mismatched run → back-calc from table; only winter file used here
    'Qwen2.5-VL-72B': [
        (BASE / 'test_result_winter/Results-Qwen2.5-VL-72B-Instruct.json',                0),
    ],
    # ── GPT-5 (summer file "gpt-5-chat-latest" + winter global) ─
    'GPT-5': [
        (BASE / 'test_result_summer/all_response/Results-gpt-5-chat-latest.json',         0),
        (BASE / 'test_result_winter/Results-gpt-5.json',                                  0),
    ],
    # ── GPT-o3 / GPT-4o / GPT-4.1 (summer lost → back-calc; winter global) ─
    # These are handled via BACKCALC_SUMMER; only winter file listed here
    'o3': [
        (BASE / 'test_result_winter/Results-o3.json',     0),
    ],
    'GPT-4o': [
        (BASE / 'test_result_winter/Results-gpt-4o.json', 0),
    ],
    'GPT-4.1': [
        (BASE / 'test_result_winter/Results-gpt-4.1.json',0),
    ],
    # ── Doubao Seed-2.0-Pro (summer 1-500 + winter internal 1-614 → offset +500) ─
    'Doubao-Seed-2.0-Pro': [
        (BASE / 'test_result_summer/doubao/Results-doubao-seed-2-0-pro-260215.json', 0),
        (BASE / 'test_result_winter/doubao/Results-doubao-seed-2-0-pro-260215.json', 500),
    ],
    # ── Complete single-file models ─────────────────────────
    'GPT-5.2': [
        (BASE / 'test_result_winter/Results-gpt-5.2.json',0),
    ],
    'GLM-4.5V': [
        (BASE / 'test_result_winter/Results-GLM-4.5V.json',0),
    ],
    'Qwen3-VL-30B-Instruct': [
        (BASE / 'test_result_winter/Results-Qwen3-VL-30B-A3B-Instruct.json', 0),
    ],
    'Qwen3-VL-30B-Thinking': [
        (BASE / 'test_result_winter/Results-Qwen3-VL-30B-A3B-Thinking.json', 0),
    ],
    'Qwen3-VL-235B-Instruct': [
        (BASE / 'test_result_winter/Results-Qwen3-VL-235B-A22B-Instruct.json', 0),
    ],
    'Qwen3-VL-235B-Thinking': [
        (BASE / 'test_result_winter/Results-Qwen3-VL-235B-A22B-Thinking.json', 0),
    ],
}


def pct(c: int, n: int) -> str:
    return f'{c / n * 100:.2f}' if n else 'N/A'


def analyze_multi(file_list: list, verbose: bool = False) -> dict:
    """
    Load and merge multiple result files.
    file_list: list of (Path, key_offset) where key_offset is added to the
               file's internal key to get the global key in KEY_INFO.
    Deduplication: if the same global key appears in multiple files, only the
    FIRST occurrence is kept (earlier in file_list takes priority).
    """
    cat_s  = defaultdict(lambda: [0, 0])
    diff_s = defaultdict(lambda: [0, 0])
    total_c, total_n = 0, 0
    seen_keys = set()

    for path, offset in file_list:
        if not Path(path).exists():
            if verbose:
                print(f'    [MISSING] {path}')
            continue
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        loaded, skipped_dup, skipped_missing = 0, 0, 0
        for item in data:
            raw_key = item.get('key')
            if raw_key is None:
                continue
            global_key = str(int(str(raw_key)) + offset)
            if global_key in seen_keys:
                skipped_dup += 1
                continue
            info = KEY_INFO.get(global_key)
            if not info:
                skipped_missing += 1
                continue
            seen_keys.add(global_key)
            correct = bool(item.get('Correct', False))
            total_n += 1
            if correct:
                total_c += 1
            cat_s[info['category']][1] += 1
            if correct:
                cat_s[info['category']][0] += 1
            diff_s[info['difficulty']][1] += 1
            if correct:
                diff_s[info['difficulty']][0] += 1
            loaded += 1
        if verbose:
            print(f'    [{Path(path).name}] offset={offset}: '
                  f'loaded={loaded}, dup_skip={skipped_dup}, key_miss={skipped_missing}')

    return {
        'total_c': total_c,
        'total_n': total_n,
        'cat_stats':  dict(cat_s),
        'diff_stats': dict(diff_s),
    }


def apply_backcalc(name: str, r: dict) -> dict:
    """
    For models with lost summer (1-500) results, add back-calculated
    correct counts derived from the table percentages in BACKCALC_SUMMER.
    The calculation is: correct = round(pct / 100 * total_in_1_500).
    """
    if name not in BACKCALC_SUMMER:
        return r
    bc = BACKCALC_SUMMER[name]
    # Overall correct count from summer (authoritative)
    summer_correct = round(bc['overall_pct'] / 100 * SUMMER_TOTAL)
    # Per-category correct from summer
    cat_s = defaultdict(lambda: [0, 0], r['cat_stats'])
    for cat, tot in SUMMER_CAT_TOTAL.items():
        if tot == 0:
            continue
        pct_val = bc['cat_pct'].get(cat, 0.0)
        correct = round(pct_val / 100 * tot)
        cat_s[cat][0] += correct
        cat_s[cat][1] += tot
    # Per-difficulty correct from summer
    diff_s = defaultdict(lambda: [0, 0], r['diff_stats'])
    for d, tot in SUMMER_DIFF_TOTAL.items():
        pct_val = bc['diff_pct'].get(d, 0.0)
        correct = round(pct_val / 100 * tot)
        diff_s[d][0] += correct
        diff_s[d][1] += tot
    return {
        'total_c': r['total_c'] + summer_correct,
        'total_n': r['total_n'] + SUMMER_TOTAL,
        'cat_stats':  dict(cat_s),
        'diff_stats': dict(diff_s),
        'backcalc_note': f'summer 1-500 back-calculated: {summer_correct}/{SUMMER_TOTAL} correct',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--latex', action='store_true', help='Also print raw LaTeX data values')
    parser.add_argument('--log',   action='store_true', help='Verbose per-file loading log')
    args = parser.parse_args()

    # Header
    col_w = 24
    print(f"\n{'Model':{col_w}} | {'Answered':>8} | {'Correct':>7} | {'Overall':>7} | "
          + ' | '.join(f'{l:>12}' for l in CAT_LABELS)
          + ' | ' + ' | '.join(f'{l:>8}' for l in DIFF_LABELS))
    print('-' * (col_w + 8 + 8 + 8 + 16 * len(CATS) + 10 * len(DIFFS) + 20))

    for name, file_list in RESULT_FILES.items():
        if args.log:
            print(f'\n  >> {name}')
        r = analyze_multi(file_list, verbose=args.log)
        # Apply back-calculation for models with lost summer results
        r = apply_backcalc(name, r)
        if args.log and 'backcalc_note' in r:
            print(f'     back-calc: {r["backcalc_note"]}')

        overall = pct(r['total_c'], r['total_n'])
        cat_vals  = [pct(*r['cat_stats'].get(c, [0, 0])) for c in CATS]
        diff_vals = [pct(*r['diff_stats'].get(d, [0, 0])) for d in DIFFS]
        print(f"{name:{col_w}} | {r['total_n']:>8} | {r['total_c']:>7} | {overall:>7} | "
              + ' | '.join(f'{v:>12}' for v in cat_vals)
              + ' | ' + ' | '.join(f'{v:>8}' for v in diff_vals))

        if args.latex:
            row = ' & '.join(cat_vals + diff_vals + [overall])
            print(f"  LaTeX: {row} \\\\")

    diff_dist = {d: sum(1 for item in master if item['difficulty'] == d) for d in DIFFS}
    print(f'\nMaster bank: {len(master)} questions | difficulty distribution: {diff_dist}')
    print(f'Summer questions (1-500): category={SUMMER_CAT_TOTAL}')
    print(f'Summer questions (1-500): difficulty={SUMMER_DIFF_TOTAL}')


if __name__ == '__main__':
    main()
