import argparse
import json
import os
import re
import time
from collections import defaultdict
from typing import Dict, List, Tuple

from tqdm import tqdm


ABILITY_LABELS = [
    "Semantic understanding",
    "Spatial understanding",
    "Temporal understanding",
    "Correspondence",
    "Visual knowledge",
    "World modeling",
]

ABILITY_SET = set(ABILITY_LABELS)
ANSWER_STEP_INDEX = "answer_step"

SYSTEM_PROMPT = """You are a vision-language reasoning expert.

Task:
Given a video QA question, classify each numbered step and the final unnumbered answer request into exactly one of the 6 predefined visual abilities.

Allowed labels (must be exact string match):
1) Semantic understanding
2) Spatial understanding
3) Temporal understanding
4) Correspondence
5) Visual knowledge
6) World modeling

Definitions:
- Semantic understanding: Identify object categories, attributes (shape/color/material), and high-level semantic relations (roles/interactions).
- Spatial understanding: Scene layout reasoning, relative geometry (left/right/front/back/near/far), and occlusion relations.
- Temporal understanding: Track motion patterns and localize events on the timeline (before/after/during).
- Correspondence: Match instance/part across time or viewpoints (same object across shots, local-to-global matching).
- Visual knowledge: Requires combining visual evidence with commonsense/world knowledge.
- World modeling: Simple near-future prediction based on current dynamics.

Few-shot examples:
- "定位一头巨马怪 (马天霸)" -> Semantic understanding
- "他在冥想时面向哪个方向？" -> Spatial understanding
- "主角在什么时间戳经过了 A 点上方？" -> Temporal understanding

Output format:
Return STRICT JSON only, with this schema:
{
  "steps": [
    {
      "step_index": 1,
      "step_text": "...",
            "abilities": [
                "One or more labels from the 6 allowed labels"
            ]
        },
        {
            "step_index": "answer_step",
            "step_text": "Final unnumbered question sentence that asks for the answer",
                        "abilities": [
                            "One or more labels from the 6 allowed labels"
                        ]
    }
  ]
}

Rules:
- Do not add extra keys.
- Do not include explanations.
- Each step must have one or more labels from the allowed labels.
- Multi-label is encouraged when a step touches multiple abilities.
- You MUST include exactly one extra step with step_index="answer_step" for the final unnumbered answer request.
- Keep numbered steps first (if present), and answer_step as the final item.
- If explicit numbered steps do not exist, return one step only with step_index="answer_step" and full question text.
- Temporal understanding is a priority label: when in doubt, include it.
- Temporal coverage requirement: at least 70% of returned steps (including answer_step) must include Temporal understanding.

Liberal labeling policy (important):
- If a step has any direction, relative position, viewpoint, geometry, lane, side, front/back/left/right, alignment, overlap, nearest/farthest, or imagined orientation, include Spatial understanding.
- If a step has any timeline cue (beginning, later, then, when, before, after, first appears, at that moment, during), include Temporal understanding.
- If a step links identity/attribute across moments or references (same color A, same person/object, corresponding target), include Correspondence.
- If a step even slightly needs commonsense/background knowledge (brand, function, world fact, search online), include Visual knowledge.
- If a step is hypothetical, imagined, counterfactual, path planning, turning, future-state or perspective transformation, include World modeling.
- Even without explicit time words, if answering a step depends on watching progression across frames or choosing a moment in video flow, include Temporal understanding.
- If the question has any sequencing cue anywhere, default to assigning Temporal understanding to most steps unless clearly impossible.
- Prefer recall over precision for: Spatial understanding, Temporal understanding, Correspondence, Visual knowledge, World modeling.
"""


def call_doubao(
    api_key: str,
    model: str,
    messages: List[Dict],
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3",
    proxy: str = None,
) -> str:
    try:
        from openai import OpenAI  # pyright: ignore[reportMissingImports]
    except ImportError as e:
        raise ImportError("The 'openai' package is required. Install with: pip install openai") from e

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy

    client = OpenAI(api_key=api_key, base_url=base_url)

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )

    if not resp.choices:
        return ""

    msg = resp.choices[0].message
    if isinstance(msg.content, str):
        return msg.content.strip()
    return str(msg.content)


def _extract_json_block(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        return fenced.group(1)

    raw = re.search(r"(\{.*\})", text, re.DOTALL)
    if raw:
        return raw.group(1)

    raise ValueError("No JSON object found in model response")


def _normalize_ability(label: str) -> str:
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


def _normalize_abilities(item: Dict) -> List[str]:
    raw_abilities = item.get("abilities")
    candidates: List[str] = []

    if isinstance(raw_abilities, list):
        candidates.extend(str(v) for v in raw_abilities)
    elif isinstance(raw_abilities, str):
        candidates.append(raw_abilities)

    # Backward compatibility for older schema that returns a single "ability" key.
    if "ability" in item:
        candidates.append(str(item.get("ability", "")))

    normalized: List[str] = []
    seen = set()
    for c in candidates:
        ability = _normalize_ability(c)
        if ability and ability not in seen:
            normalized.append(ability)
            seen.add(ability)

    return normalized


def parse_and_validate_response(raw_text: str) -> List[Dict]:
    json_block = _extract_json_block(raw_text)
    data = json.loads(json_block)

    if not isinstance(data, dict) or "steps" not in data or not isinstance(data["steps"], list):
        raise ValueError("Response JSON must contain a list field: steps")

    validated_steps = []
    for i, item in enumerate(data["steps"], start=1):
        if not isinstance(item, dict):
            continue
        step_text = str(item.get("step_text", "")).strip()
        abilities = _normalize_abilities(item)
        step_index = item.get("step_index", i)

        if not abilities:
            raise ValueError(f"Invalid abilities in step {i}: {item.get('abilities') or item.get('ability')}")

        if isinstance(step_index, int):
            normalized_step_index = step_index
        else:
            step_index_str = str(step_index).strip()
            if step_index_str.isdigit():
                normalized_step_index = int(step_index_str)
            elif step_index_str.lower().replace(" ", "_") == ANSWER_STEP_INDEX:
                normalized_step_index = ANSWER_STEP_INDEX
            else:
                normalized_step_index = step_index_str or i

        validated_steps.append(
            {
                "step_index": normalized_step_index,
                "step_text": step_text,
                "abilities": abilities,
            }
        )

    if not validated_steps:
        raise ValueError("No valid steps parsed from response")

    has_answer_step = any(step.get("step_index") == ANSWER_STEP_INDEX for step in validated_steps)
    if not has_answer_step:
        raise ValueError("Missing required answer_step in response")

    return validated_steps


def classify_question(
    api_key: str,
    model_name: str,
    question_text: str,
    base_url: str,
    proxy: str,
    max_retries: int,
) -> Tuple[List[Dict], str]:
    user_prompt = (
        "Classify the following question steps into the 6 abilities (multi-label). "
        "Return strict JSON only. "
        "Important: include the final unnumbered answer request as an additional step with step_index='answer_step'. "
        "Use one or more labels per step with key 'abilities'. "
        "For Spatial/Temporal/Correspondence/Visual knowledge/World modeling, use a low threshold and include them if even weakly related. "
        "Temporal-priority requirement: at least 70% of returned steps (including answer_step) must include Temporal understanding; when uncertain, include Temporal understanding.\n\n"
        f"Question:\n{question_text}"
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_error = ""
    raw_response = ""
    for _ in range(max_retries + 1):
        raw_response = call_doubao(api_key, model_name, messages, base_url, proxy)
        try:
            steps = parse_and_validate_response(raw_response)
            return steps, raw_response
        except Exception as e:
            last_error = str(e)
            repair_prompt = (
                "Your previous output did not match schema or labels. "
                "Please regenerate STRICT JSON with keys exactly: steps -> [{step_index, step_text, abilities}]. "
                "You MUST include exactly one item with step_index='answer_step' for the final unnumbered answer request. "
                "Each abilities must be a non-empty list and each label must be one of: "
                + ", ".join(ABILITY_LABELS)
                + ". For Spatial/Temporal/Correspondence/Visual knowledge/World modeling, include labels if weakly relevant. "
                + "Temporal understanding must appear in at least 70% of returned steps (including answer_step)."
            )
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user", "content": repair_prompt})

    fallback_steps = [
        {
            "step_index": ANSWER_STEP_INDEX,
            "step_text": question_text,
            "abilities": ["Semantic understanding"],
        }
    ]
    raw_fallback = f"PARSE_ERROR: {last_error}; RAW: {raw_response}"
    return fallback_steps, raw_fallback


def build_statistics(records: List[Dict]) -> Dict:
    counts = defaultdict(int)
    total_steps = 0
    total_ability_assignments = 0

    for rec in records:
        for st in rec.get("step_abilities", []):
            raw_abilities = st.get("abilities")
            if isinstance(raw_abilities, list):
                step_abilities = [str(v) for v in raw_abilities]
            else:
                # Backward compatibility for previous single-label output.
                legacy_ability = st.get("ability")
                step_abilities = [str(legacy_ability)] if legacy_ability else []

            normalized = []
            seen = set()
            for label in step_abilities:
                ability = _normalize_ability(label)
                if ability and ability not in seen:
                    normalized.append(ability)
                    seen.add(ability)

            if not normalized:
                continue

            total_steps += 1
            for ability in normalized:
                counts[ability] += 1
                total_ability_assignments += 1

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


def save_txt_report(stats: Dict, output_path: str) -> None:
    lines = []
    lines.append("Step Ability Statistics")
    lines.append("=" * 36)
    lines.append(f"Total questions: {stats['total_questions']}")
    lines.append(f"Total steps: {stats['total_steps']}")
    lines.append(f"Total ability assignments: {stats.get('total_ability_assignments', stats['total_steps'])}")
    lines.append("")
    lines.append(f"{'Ability':<28}{'Count':>8}{'Percent':>10}")
    lines.append("-" * 46)

    for ability in ABILITY_LABELS:
        item = stats["abilities"][ability]
        lines.append(f"{ability:<28}{item['count']:>8}{item['percentage']:>9.2f}%")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def atomic_dump_json(output_path: str, data: List[Dict]) -> None:
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, output_path)


def make_resume_id(key: object, question: str, index: int) -> str:
    key_str = str(key or "").strip()
    if key_str:
        return f"key::{key_str}"

    question_str = str(question or "").strip()
    if question_str:
        return f"question::{question_str}"

    return f"idx::{index}"


def is_failed_record(record: Dict) -> bool:
    raw_response = str(record.get("raw_response", ""))
    if raw_response.startswith("REQUEST_ERROR:"):
        return True
    return raw_response.startswith("PARSE_ERROR:")


def load_existing_results(output_json: str) -> List[Dict]:
    if not os.path.exists(output_json) or os.path.getsize(output_json) == 0:
        return []

    try:
        with open(output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        # Preserve broken content for manual inspection and start fresh.
        backup_path = output_json + ".broken"
        try:
            os.replace(output_json, backup_path)
        except Exception:
            pass
        return []


def build_processed_ids(existing_results: List[Dict], retry_failed: bool) -> set:
    processed_ids = set()
    for idx, rec in enumerate(existing_results, start=1):
        rid = make_resume_id(rec.get("key"), str(rec.get("question", "")), idx)
        if not retry_failed or not is_failed_record(rec):
            processed_ids.add(rid)
    return processed_ids


def run(
    input_json: str,
    output_json: str,
    stats_json: str,
    stats_txt: str,
    model_name: str,
    api_key: str,
    base_url: str,
    proxy: str,
    max_retries: int,
    sleep_seconds: float,
    retry_failed: bool,
    continue_on_error: bool,
) -> None:
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list of question items")

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    os.makedirs(os.path.dirname(stats_json), exist_ok=True)
    os.makedirs(os.path.dirname(stats_txt), exist_ok=True)

    results = load_existing_results(output_json)
    processed_ids = build_processed_ids(results, retry_failed=retry_failed)

    indexed_data = list(enumerate(data, start=1))
    indexed_data.reverse()

    for original_idx, item in tqdm(indexed_data, desc="Classifying (reverse)"):
        question = str(item.get("question", "")).strip()
        resume_id = make_resume_id(item.get("key"), question, original_idx)

        if resume_id in processed_ids:
            continue

        if not question:
            continue

        try:
            step_abilities, raw_response = classify_question(
                api_key=api_key,
                model_name=model_name,
                question_text=question,
                base_url=base_url,
                proxy=proxy,
                max_retries=max_retries,
            )
        except Exception as e:
            step_abilities = []
            raw_response = f"REQUEST_ERROR: {type(e).__name__}: {e}"

            result_item = {
                "key": item.get("key"),
                "video_id": item.get("video_id"),
                "category": item.get("category"),
                "question": question,
                "step_abilities": step_abilities,
                "raw_response": raw_response,
            }
            results.append(result_item)
            atomic_dump_json(output_json, results)

            if not retry_failed:
                processed_ids.add(resume_id)

            if not continue_on_error:
                raise

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
            continue

        result_item = {
            "key": item.get("key"),
            "video_id": item.get("video_id"),
            "category": item.get("category"),
            "question": question,
            "step_abilities": step_abilities,
            "raw_response": raw_response,
        }
        results.append(result_item)
        processed_ids.add(resume_id)

        atomic_dump_json(output_json, results)

        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    stats = build_statistics(results)

    with open(stats_json, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    save_txt_report(stats, stats_txt)

    print("\nDone.")
    print(f"Results JSON: {output_json}")
    print(f"Stats JSON:   {stats_json}")
    print(f"Stats TXT:    {stats_txt}")


def main():
    parser = argparse.ArgumentParser(
        description="Classify each question step into 6 visual abilities using Doubao API (reverse order)"
    )
    parser.add_argument(
        "--input_json",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/winter_ques/1-1114.json",
        type=str,
        help="Path to source QA JSON file",
    )
    parser.add_argument(
        "--output_json",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result/step_ability_results_reverse.json",
        type=str,
        help="Path to per-question step ability output JSON",
    )
    parser.add_argument(
        "--stats_json",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result/step_ability_stats_reverse.json",
        type=str,
        help="Path to aggregated statistics JSON",
    )
    parser.add_argument(
        "--stats_txt",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result/step_ability_stats_reverse.txt",
        type=str,
        help="Path to aggregated statistics TXT report",
    )
    parser.add_argument(
        "--model_name",
        default="Qwen3.5-122B-A10B",
        type=str,
        help="Doubao model name",
    )
    parser.add_argument(
        "--api_key",
        default=None,
        type=str,
        help="Doubao API key (or set ARK_API_KEY env var)",
    )
    parser.add_argument(
        "--base_url",
        default="https://llmapi.paratera.com",
        type=str,
        help="Doubao API base URL",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        type=str,
        help="Proxy URL (optional)",
    )
    parser.add_argument(
        "--max_retries",
        default=2,
        type=int,
        help="Retries when response format is invalid",
    )
    parser.add_argument(
        "--sleep_seconds",
        default=0.0,
        type=float,
        help="Sleep seconds between requests",
    )
    parser.add_argument(
        "--retry_failed",
        default=1,
        type=int,
        choices=[0, 1],
        help="1: retry failed records when resuming; 0: skip failed records too",
    )
    parser.add_argument(
        "--continue_on_error",
        default=1,
        type=int,
        choices=[0, 1],
        help="1: continue when one request fails; 0: raise immediately",
    )

    args = parser.parse_args()

    api_key = args.api_key or os.getenv("ARK_API_KEY")
    if not api_key:
        raise ValueError("API key must be provided via --api_key or ARK_API_KEY environment variable")

    run(
        input_json=args.input_json,
        output_json=args.output_json,
        stats_json=args.stats_json,
        stats_txt=args.stats_txt,
        model_name=args.model_name,
        api_key=api_key,
        base_url=args.base_url,
        proxy=args.proxy,
        max_retries=args.max_retries,
        sleep_seconds=args.sleep_seconds,
        retry_failed=bool(args.retry_failed),
        continue_on_error=bool(args.continue_on_error),
    )


if __name__ == "__main__":
    main()
