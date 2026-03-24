#!/usr/bin/env python3
"""
Template runner for plugging your own model into PerceptionComp.

Recommended workflow:

1. Copy this file to a new filename, for example:

   cp evaluate/tools/runners/custom_template.py evaluate/tools/runners/my_model.py

2. Implement `run_your_model(...)`.

3. Run:

   python evaluate/evaluate.py \
     --model my-model \
     --provider custom \
     --custom-runner evaluate/tools/runners/my_model.py \
     --video-dir benchmark/videos
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path


def load_custom_config(custom_config):
    if custom_config is None:
        return {}
    if isinstance(custom_config, dict):
        return custom_config
    path = Path(custom_config)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(f"Custom config file not found: {custom_config}")


def sample_video_frames(video_path: str, num_frames: int = 8, resize_short_side: int = 720):
    try:
        import cv2
    except ImportError as e:
        raise ImportError(
            "OpenCV is required for the default transformers example. "
            "Install it with `pip install opencv-python`."
        ) from e

    try:
        from PIL import Image
    except ImportError as e:
        raise ImportError(
            "Pillow is required for the default transformers example. "
            "Install it with `pip install pillow`."
        ) from e

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if frame_count <= 0:
        cap.release()
        raise RuntimeError(f"No frames found in video: {video_path}")

    import numpy as np

    idxs = np.linspace(0, frame_count - 1, num=min(num_frames, frame_count), dtype=int)
    frames = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        h, w = frame.shape[:2]
        short_side = min(h, w)
        if resize_short_side and short_side > resize_short_side:
            scale = resize_short_side / short_side
            frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(frame))

    cap.release()
    if not frames:
        raise RuntimeError(f"Failed to decode frames from: {video_path}")
    return frames


def run_with_transformers(video_path: str, prompt: str, model_name: str, custom_config=None):
    config = load_custom_config(custom_config)

    try:
        import torch
        from transformers import AutoModelForVision2Seq, AutoProcessor
    except ImportError as e:
        raise ImportError(
            "The default custom template uses local Hugging Face transformers. "
            "Install the required packages, for example: "
            "`pip install transformers torch pillow`."
        ) from e

    model_path = config.get("model_path") or model_name
    num_frames = int(config.get("num_frames", 8))
    max_new_tokens = int(config.get("max_new_tokens", 128))
    trust_remote_code = bool(config.get("trust_remote_code", True))
    device = config.get("device") or ("cuda" if torch.cuda.is_available() else "cpu")
    dtype_name = str(config.get("dtype", "auto")).lower()

    torch_dtype = None
    if dtype_name == "bfloat16":
        torch_dtype = torch.bfloat16
    elif dtype_name == "float16":
        torch_dtype = torch.float16
    elif dtype_name == "float32":
        torch_dtype = torch.float32

    frames = sample_video_frames(video_path, num_frames=num_frames)

    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=trust_remote_code
    )
    model = AutoModelForVision2Seq.from_pretrained(
        model_path,
        trust_remote_code=trust_remote_code,
        torch_dtype=torch_dtype,
    )
    model.to(device)
    model.eval()

    messages = [
        {
            "role": "user",
            "content": (
                [{"type": "image", "image": image} for image in frames]
                + [{"type": "text", "text": prompt}]
            ),
        }
    ]

    if hasattr(processor, "apply_chat_template"):
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = processor(
            text=[text],
            images=frames,
            padding=True,
            return_tensors="pt",
        )
    else:
        inputs = processor(
            text=[prompt],
            images=frames,
            padding=True,
            return_tensors="pt",
        )

    model_inputs = {}
    for key, value in inputs.items():
        if hasattr(value, "to"):
            model_inputs[key] = value.to(device)
        else:
            model_inputs[key] = value

    with torch.no_grad():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
        )

    if "input_ids" in model_inputs:
        input_len = model_inputs["input_ids"].shape[-1]
        generated_ids = generated_ids[:, input_len:]

    text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=True,
    )[0]
    return text.strip()


def run_your_model(video_path: str, prompt: str, model_name: str, custom_config=None):
    """
    Default behavior:
    - treat the runner as a local Hugging Face transformers example
    - sample frames from the input video
    - pass them to a vision-language model
    - return the raw generated text

    If this does not match your stack, replace this function with your own
    inference code and keep the rest of the benchmark protocol unchanged.

    Expected return:
    - a raw string response from the model
    - ideally ending with `Answer: X` where X is one of A/B/C/D/E

    You can implement this with:
    - a local Transformers model
    - a private inference server
    - a custom SDK
    - a shell wrapper around your own evaluation code
    """
    return run_with_transformers(
        video_path=video_path,
        prompt=prompt,
        model_name=model_name,
        custom_config=custom_config,
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
