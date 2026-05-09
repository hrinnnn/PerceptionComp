import csv
import json
import math
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


LETTERS = "ABCDE"

SAFETY_SETTINGS = {
    "HATE": "BLOCK_NONE",
    "HARASSMENT": "BLOCK_NONE",
    "SEXUAL": "BLOCK_NONE",
    "DANGEROUS": "BLOCK_NONE",
}


@dataclass
class SampledFrames:
    parts: list[dict[str, Any]]
    timestamps: list[float]
    duration: float


def require_cv2():
    try:
        import cv2
    except ImportError as e:
        raise ImportError("OpenCV is required for agentic Gemini sampling. Install it with `pip install opencv-python`.") from e
    return cv2


def require_numpy():
    try:
        import numpy as np
    except ImportError as e:
        raise ImportError("NumPy is required for agentic Gemini sampling. Install it with `pip install numpy`.") from e
    return np


def progress(iterable):
    try:
        from tqdm import tqdm
    except ImportError:
        return iterable
    return tqdm(iterable)


def get_video_duration(path: str) -> float:
    cv2 = require_cv2()
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    if fps <= 0 or frame_count <= 0:
        raise RuntimeError(f"Cannot determine video duration: {path}")
    return float(frame_count / fps)


def sample_video_frames(
    path: str,
    num_frames: int,
    resize: int = 336,
    start_time: float | None = None,
    end_time: float | None = None,
) -> SampledFrames:
    cv2 = require_cv2()
    np = require_numpy()
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if fps <= 0 or frame_count <= 0:
        cap.release()
        raise RuntimeError(f"No frames found in video: {path}")

    duration = frame_count / fps
    start = max(0.0, float(start_time if start_time is not None else 0.0))
    end = min(float(end_time if end_time is not None else duration), duration)
    if end <= start:
        cap.release()
        raise ValueError(f"Invalid sample window [{start}, {end}] for duration {duration:.2f}s")

    sample_count = max(1, int(num_frames))
    times = np.linspace(start, end, num=sample_count, endpoint=True)
    parts: list[dict[str, Any]] = []
    timestamps: list[float] = []

    for timestamp in times:
        frame_idx = min(frame_count - 1, max(0, int(round(timestamp * fps))))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        if resize:
            h, w = frame.shape[:2]
            short_side = min(h, w)
            if short_side > resize:
                scale = resize / short_side
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)))
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue
        parts.append({"mime_type": "image/jpeg", "data": buf.tobytes()})
        timestamps.append(float(frame_idx / fps))

    cap.release()
    if not parts:
        raise RuntimeError(f"Failed to decode frames from: {path}")
    return SampledFrames(parts=parts, timestamps=timestamps, duration=float(duration))


def crop_frame_count_for_window(window: dict[str, Any], max_crop_frames: int) -> int:
    duration = max(0.0, float(window["end_time"]) - float(window["start_time"]))
    return max(1, min(int(max_crop_frames), int(math.ceil(duration))))


def format_options(item: dict[str, Any]) -> str:
    options = []
    for i, letter in enumerate(LETTERS):
        choice_key = f"answer_choice_{i}"
        if choice_key in item:
            options.append(f"{letter}: {item[choice_key]}")
    return ", ".join(options)


def build_initial_prompt(
    item: dict[str, Any],
    options_str: str,
    duration: float,
    frame_times: list[float],
    video_file: str,
    max_tool_rounds: int,
) -> str:
    return (
        "You are a video reasoning agent evaluating a multiple-choice PerceptionComp question.\n"
        "You will first see sparse frames sampled from the whole video. If the evidence is insufficient, "
        "request a closer temporal inspection. The evaluator will crop that clip, sample frames from it, "
        "and send those frames back in the same conversation.\n"
        f"Video duration: {duration:.2f} seconds.\n"
        f"Video path: {video_file}\n"
        f"Whole-video sampled frame timestamps: {', '.join(f'{t:.2f}s' for t in frame_times)}.\n\n"
        f"Question: {item.get('question')}\n"
        f"Options: {options_str}\n\n"
        "Evidence policy:\n"
        "- Before answering, check whether the observed frames give direct visual evidence for every critical part "
        "of the question and for rejecting the other plausible options.\n"
        "- Do not answer from plausibility, world knowledge, or partial evidence. If any key scene, object, action, "
        "spatial relation, temporal relation, or option distinction is not directly visible, you must request "
        "an <inspect> window.\n"
        "- If two or more options remain plausible, request an <inspect> window targeted at distinguishing those "
        "options instead of guessing.\n\n"
        "High-risk question types:\n"
        "- If the question asks about before/after/order, a relative position, a small or briefly visible object, "
        "a specific person/action, counting occurrences, or a detail tied to one short scene, you should perform "
        "at least one <inspect> unless the answer is directly and unambiguously visible in the sampled frames.\n\n"
        f"You may request at most {max_tool_rounds} temporal inspections.\n"
        "Each <inspect> request consumes one inspection. After the inspection budget is exhausted, "
        "you must stop requesting clips and give the best possible <answer> based on the evidence already shown.\n"
        "CRITICAL OUTPUT RULE: Every response must contain EITHER exactly one <inspect> block "
        "OR exactly one <answer> block — NEVER both. If you request an <inspect> you MUST NOT "
        "include an <answer> in the same response. If you give an <answer> you MUST NOT include "
        "an <inspect>.\n\n"
        "If you need more evidence, output exactly:\n"
        "<think>brief reasoning about what evidence is missing</think>\n"
        "<inspect>{\"start_time\": 0.0, \"end_time\": 10.0, \"reason\": \"why this clip matters\"}</inspect>\n\n"
        "If you are ready to answer, output exactly:\n"
        "<think>reasoning based only on observed evidence</think>\n"
        "<answer>X</answer>\n"
        "Inside <answer>, output only one capital letter from A, B, C, D, or E."
    )


def build_observation_prompt(
    window: dict[str, Any],
    timestamps: list[float],
    remaining_rounds: int,
) -> str:
    if remaining_rounds > 0:
        next_step = (
            f"You have {remaining_rounds} inspection request(s) remaining. "
            "If this clip is still insufficient, you may request another <inspect> window. "
            "Otherwise answer now."
        )
    else:
        next_step = (
            "You have 0 inspection requests remaining. This was the final allowed inspection. "
            "Do not request another clip; you must answer now."
        )

    return (
        f"Observation from crop_video: cropped {window['start_time']:.2f}s-{window['end_time']:.2f}s. "
        f"Frame timestamps: {', '.join(f'{t:.2f}s' for t in timestamps)}.\n"
        f"Reason for this crop: {window.get('reason', '')}\n"
        "Now reassess the evidence. Answer only if this clip and the previous frames directly support one option "
        "and rule out the other plausible options. If a key detail is still missing or two options remain plausible, "
        "request another targeted <inspect> window while you still have inspection budget.\n"
        f"{next_step}\n"
        "CRITICAL: Output EITHER <inspect> OR <answer> — NEVER both in the same response.\n"
        "Use exactly one of: <inspect>{...}</inspect> or <answer>X</answer>."
    )


def parse_prediction(raw_response: str) -> tuple[str, str]:
    thinking = raw_response.strip()
    think_matches = re.findall(r"<think>\s*(.*?)\s*</think>", raw_response, re.DOTALL | re.IGNORECASE)
    if think_matches:
        thinking = think_matches[-1].strip()

    answer_matches = re.findall(r"<answer>\s*(.*?)\s*</answer>", raw_response, re.DOTALL | re.IGNORECASE)
    if answer_matches:
        choice = answer_matches[-1].strip()
    else:
        direct = re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE)
        if direct:
            choice = direct.group(1)
        else:
            letters = re.findall(r"\b([A-E])\b", raw_response.upper())
            choice = letters[-1] if letters else ""

    letters = re.findall(r"\b([A-E])\b", str(choice).upper())
    return (letters[-1] if letters else "WRONG"), thinking


def has_explicit_answer(raw_response: str) -> bool:
    if re.search(r"<answer>\s*.*?\s*</answer>", raw_response, re.DOTALL | re.IGNORECASE):
        return True
    return re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE) is not None


def extract_inspect_request(raw_response: str) -> dict[str, Any] | None:
    matches = re.findall(r"<inspect>\s*(.*?)\s*</inspect>", raw_response, re.DOTALL | re.IGNORECASE)
    candidates = matches or re.findall(r"\{[^{}]*start_time[^{}]*end_time[^{}]*\}", raw_response, re.DOTALL)
    for candidate in candidates:
        try:
            parsed = json.loads(candidate.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "start_time" in parsed and "end_time" in parsed:
            return parsed
    return None


def normalize_inspect_request(
    request: dict[str, Any],
    duration: float,
    min_window_seconds: float,
) -> dict[str, Any] | None:
    try:
        start = float(request["start_time"])
        end = float(request["end_time"])
    except (TypeError, ValueError):
        return None

    start = max(0.0, min(start, duration))
    end = max(0.0, min(end, duration))
    if end <= start:
        return None

    if end - start < min_window_seconds:
        midpoint = (start + end) / 2
        half = min_window_seconds / 2
        start = max(0.0, midpoint - half)
        end = min(duration, midpoint + half)
        if end - start < min_window_seconds:
            start = max(0.0, end - min_window_seconds)

    return {
        "start_time": start,
        "end_time": end,
        "reason": str(request.get("reason", "")).strip(),
    }


def configure_gemini(api_key: str, proxy: str | None = None):
    import google.generativeai as genai

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy for Gemini calls: {proxy}")

    genai.configure(api_key=api_key)
    return genai


def send_chat_message_with_retry(chat: Any, parts: list[Any], max_retries: int = 2) -> Any:
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return chat.send_message(
                parts,
                request_options={"timeout": 600},
                safety_settings=SAFETY_SETTINGS,
            )
        except Exception as e:
            last_error = e
            if attempt >= max_retries:
                break
            sleep_for = 2 * (attempt + 1)
            print(f"Gemini call failed, retrying in {sleep_for}s: {e}")
            time.sleep(sleep_for)
    raise last_error


def response_text(response: Any) -> str:
    try:
        return response.text or ""
    except Exception:
        return str(response)


def run_agentic_prediction(
    api_key: str,
    model_name: str,
    item: dict[str, Any],
    video_file: str,
    proxy: str | None,
    rounds: int,
    global_frames: int,
    crop_frames: int,
    min_window_seconds: float,
) -> dict[str, Any]:
    genai = configure_gemini(api_key, proxy)
    model = genai.GenerativeModel(model_name=model_name)
    chat = model.start_chat(history=[])

    duration = get_video_duration(video_file)
    options_str = format_options(item)
    inspected_windows: list[dict[str, Any]] = []
    round_records: list[dict[str, Any]] = []
    final_response = ""

    global_sampled = sample_video_frames(video_file, num_frames=global_frames)
    initial_prompt = build_initial_prompt(
        item=item,
        options_str=options_str,
        duration=duration,
        frame_times=global_sampled.timestamps,
        video_file=video_file,
        max_tool_rounds=max(0, rounds),
    )

    response = send_chat_message_with_retry(chat, [*global_sampled.parts, initial_prompt])
    final_response = response_text(response)

    for round_index in range(max(0, rounds) + 1):
        raw_inspect = extract_inspect_request(final_response)
        answer, thinking = parse_prediction(final_response)
        if raw_inspect is not None and round_index < max(0, rounds):
            answer = "WRONG"

        normalized_inspect = (
            normalize_inspect_request(raw_inspect, duration, min_window_seconds) if raw_inspect else None
        )
        round_record = {
            "round": round_index + 1,
            "raw_response": final_response,
            "parsed_answer": answer,
            "thinking": thinking,
            "inspect_request": normalized_inspect,
            "chat_history_length": len(getattr(chat, "history", []) or []),
        }

        if answer != "WRONG":
            round_records.append(round_record)
            break

        if normalized_inspect is None or round_index >= max(0, rounds):
            round_records.append(round_record)
            break

        sampled = sample_video_frames(
            video_file,
            num_frames=crop_frame_count_for_window(normalized_inspect, crop_frames),
            start_time=normalized_inspect["start_time"],
            end_time=normalized_inspect["end_time"],
        )
        inspected_windows.append(normalized_inspect)
        observation_prompt = build_observation_prompt(
            normalized_inspect,
            sampled.timestamps,
            remaining_rounds=max(0, rounds) - len(inspected_windows),
        )
        round_record.update(
            {
                "crop_frame_count": len(sampled.parts),
                "crop_frame_timestamps": sampled.timestamps,
            }
        )
        round_records.append(round_record)

        response = send_chat_message_with_retry(chat, [*sampled.parts, observation_prompt])
        final_response = response_text(response)

    predicted, thinking = parse_prediction(final_response)
    if extract_inspect_request(final_response) is not None and not has_explicit_answer(final_response):
        predicted = "WRONG"
    # If both inspect request and answer are present after budget exhausted,
    # prioritize the answer (cannot inspect further).

    return {
        "predicted": predicted,
        "thinking": thinking,
        "raw_response": final_response,
        "rounds": round_records,
        "inspected_windows": inspected_windows,
        "video_duration": duration,
        "message_count": len(getattr(chat, "history", []) or []),
        "initial_frame_timestamps": global_sampled.timestamps,
    }


def evaluate(
    video_path: str,
    json_file_path: str,
    output_path: str,
    model_name: str,
    api_key: str,
    proxy: str | None = None,
    rounds: int = 5,
    global_frames: int = 64,
    crop_frames: int = 128,
    min_window_seconds: float = 2.0,
    max_samples: int | None = None,
):
    if "gemini" not in model_name.lower():
        raise ValueError("agentic-gemini provider expects a Gemini model name")

    os.makedirs(output_path, exist_ok=True)
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    categories = []
    for item in data:
        category = item.get("category", "Unknown")
        if category not in categories:
            categories.append(category)

    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)
    output_records: list[dict[str, Any]] = []
    json_file_output = os.path.join(output_path, f"Results-{model_name}-agentic-gemini.json")

    processed_keys = set()
    if os.path.exists(json_file_output) and os.path.getsize(json_file_output) > 0:
        try:
            with open(json_file_output, "r", encoding="utf-8") as f:
                output_records = json.load(f)
            for record in output_records:
                key = record.get("key")
                if key:
                    processed_keys.add(key)
                category = record.get("Category", "Unknown")
                total_counts[category] += 1
                if record.get("Correct"):
                    correct_counts[category] += 1
        except Exception as e:
            print(f"Warning: failed to load existing results file: {e}")
            output_records = []
            processed_keys = set()

    evaluated_this_run = 0
    for item in progress(data):
        if max_samples is not None and evaluated_this_run >= max_samples:
            print(f"Reached --max-samples={max_samples}; stopping early.")
            break

        key = item.get("key")
        if key in processed_keys:
            print(f"Skipping already processed: {key}")
            continue

        video_id = item.get("video_id")
        video_file = os.path.join(video_path, f"{video_id}.mp4")
        category = item.get("category", "Unknown")
        correct_answer = LETTERS[int(item.get("answer_id", 0))]
        options_str = format_options(item)

        if not os.path.exists(video_file):
            print(f"Video not found, skipping: {video_file}")
            continue

        try:
            prediction = run_agentic_prediction(
                api_key=api_key,
                model_name=model_name,
                item=item,
                video_file=video_file,
                proxy=proxy,
                rounds=rounds,
                global_frames=global_frames,
                crop_frames=crop_frames,
                min_window_seconds=min_window_seconds,
            )
        except Exception as e:
            print(f"Error predicting for {key}: {e}")
            prediction = {
                "predicted": "WRONG",
                "thinking": f"ERROR: {e}",
                "raw_response": f"ERROR: {e}",
                "rounds": [],
                "inspected_windows": [],
                "video_duration": None,
                "message_count": None,
                "initial_frame_timestamps": [],
            }

        predicted_answer = prediction["predicted"]
        is_correct = predicted_answer == correct_answer
        total_counts[category] += 1
        if is_correct:
            correct_counts[category] += 1

        output_records.append(
            {
                "key": key,
                "video_id": video_id,
                "Question": item.get("question"),
                "Options": options_str,
                "GT": correct_answer,
                "Predicted Answer": predicted_answer,
                "Thinking": prediction["thinking"],
                "Correct": is_correct,
                "Category": category,
                "Difficulty": item.get("difficulty"),
                "all_response": prediction["raw_response"],
                "agentic_rounds": prediction["rounds"],
                "inspected_windows": prediction["inspected_windows"],
                "video_duration": prediction["video_duration"],
                "message_count": prediction.get("message_count"),
                "initial_frame_timestamps": prediction.get("initial_frame_timestamps"),
                "agentic_config": {
                    "max_crop_rounds": rounds,
                    "global_frames": global_frames,
                    "crop_frames": crop_frames,
                    "min_window_seconds": min_window_seconds,
                    "conversation_backend": "google.generativeai chat",
                },
            }
        )

        with open(json_file_output, "w", encoding="utf-8") as f:
            json.dump(output_records, f, indent=2, ensure_ascii=False)
        evaluated_this_run += 1

    accuracies = {
        cat: (correct_counts[cat] / total_counts[cat] if total_counts[cat] > 0 else 0)
        for cat in categories
    }
    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    overall_accuracy = total_correct / total_questions if total_questions > 0 else 0

    csv_file = os.path.join(output_path, f"Results-{model_name}-agentic-gemini.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = list(categories) + ["Overall Accuracy", "Total Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        row = {cat: f"{accuracies.get(cat, 0):.3f}" for cat in categories}
        row["Overall Accuracy"] = f"{overall_accuracy:.3f}"
        row["Total Questions"] = str(total_questions)
        writer.writerow(row)

    print("\nAgentic Gemini evaluation complete!")
    print(f"Overall Accuracy: {overall_accuracy:.3f}")
    print(f"Total Questions: {total_questions}")
    print(f"Results: {json_file_output}")
