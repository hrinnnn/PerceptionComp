#!/usr/bin/env python3
"""
Template runner for plugging your own model into PerceptionComp.

Usage example:

python evaluate/evaluate.py \
  --model my-model \
  --provider custom \
  --custom-runner evaluate/tools/runners/custom_template.py \
  --video-dir benchmark/videos \
  --annotations benchmark/annotations/official/1-1114.json
"""

import json
import os
import re
from collections import defaultdict


def run_your_model(video_path: str, prompt: str, model_name: str, custom_config=None):
    """
    Replace this function with your own inference code.

    Expected return:
    - a raw string response from the model
    - ideally ending with `Answer: X` where X is one of A/B/C/D/E
    """
    raise NotImplementedError(
        "Implement `run_your_model` with your own local model, server, or SDK call."
    )


def parse_prediction(raw_response: str) -> tuple[str, str]:
    thinking = raw_response.strip()

    try:
        think_matches = re.findall(r"<think>\s*(.*?)\s*</think>", raw_response, re.DOTALL)
    except Exception:
        think_matches = []
    if think_matches:
        thinking = think_matches[-1].strip()

    choice = None
    try:
        answer_matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", raw_response, re.DOTALL)
    except Exception:
        answer_matches = []
    if answer_matches:
        choice = answer_matches[-1].strip()
    else:
        direct = re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE)
        if direct:
            choice = direct.group(1)
        else:
            letters = re.findall(r"\b([A-E])\b", raw_response.upper())
            if letters:
                choice = letters[-1]

    if not choice:
        return "WRONG", thinking

    letters = re.findall(r"\b([A-E])\b", str(choice).upper())
    return (letters[-1] if letters else "WRONG"), thinking


def evaluate(
    video_path: str,
    json_file_path: str,
    output_path: str,
    model_name: str,
    api_key=None,
    base_url=None,
    proxy=None,
    frames=64,
    custom_config=None,
):
    os.makedirs(output_path, exist_ok=True)

    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    output_records = []
    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)

    for item in data:
        key = item["key"]
        video_id = item["video_id"]
        question = item["question"]
        category = item.get("category", "Unknown")
        video_file = os.path.join(video_path, f"{video_id}.mp4")

        options = []
        for i in range(5):
            choice_key = f"answer_choice_{i}"
            if choice_key in item:
                options.append(f"{chr(65+i)}: {item[choice_key]}")

        prompt = (
            "Answer the following multiple-choice video question.\n"
            f"Question: {question}\n"
            f"Options: {', '.join(options)}\n"
            "End your response with `Answer: X` where X is A, B, C, D, or E."
        )

        raw_response = run_your_model(
            video_path=video_file,
            prompt=prompt,
            model_name=model_name,
            custom_config=custom_config,
        )
        predicted, thinking = parse_prediction(raw_response)
        gt = chr(65 + item["answer_id"])

        is_correct = predicted == gt
        total_counts[category] += 1
        if is_correct:
            correct_counts[category] += 1

        output_records.append(
            {
                "key": key,
                "video_id": video_id,
                "Question": question,
                "GT": gt,
                "Predicted Answer": predicted,
                "Thinking": thinking,
                "Correct": is_correct,
                "Category": category,
                "all_response": raw_response,
            }
        )

    output_file = os.path.join(output_path, f"Results-{model_name}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_records, f, indent=2, ensure_ascii=False)

    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    accuracy = total_correct / total_questions if total_questions else 0.0
    print(f"Saved results to: {output_file}")
    print(f"Overall accuracy: {accuracy:.4f}")
