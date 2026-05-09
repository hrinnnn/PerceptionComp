import base64
import csv
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any


LETTERS = "ABCDE"
MAX_TOOL_CALLS_PER_TURN = 5

CROP_VIDEO_TOOL = {
    "type": "function",
    "function": {
        "name": "crop_video",
        "description": (
            "Crop a video to a specified duration. Use this tool to zoom in on specific time segments "
            "for detailed analysis."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Path to the video file"},
                "start_time": {"type": "number", "description": "Start time in seconds"},
                "end_time": {"type": "number", "description": "End time in seconds"},
                "reason": {"type": "string", "description": "Why this time span should be inspected"},
            },
            "required": ["video_path", "start_time", "end_time"],
        },
    },
}

TOOL_PROMPT = (
    "Think first, call crop_video if you need to inspect a specific time segment, then answer. "
    "You may call crop_video multiple times across turns if the evidence is still insufficient. "
    "When you are ready, output <think>...</think><answer>X</answer>. "
    "Inside <answer>, output only one capital letter from A, B, C, D, or E."
)


@dataclass
class SampledFrames:
    urls: list[str]
    timestamps: list[float]
    duration: float


def require_cv2():
    try:
        import cv2
    except ImportError as e:
        raise ImportError("OpenCV is required for agentic video sampling. Install it with `pip install opencv-python`.") from e
    return cv2


def require_numpy():
    try:
        import numpy as np
    except ImportError as e:
        raise ImportError("NumPy is required for agentic video sampling. Install it with `pip install numpy`.") from e
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
    resize: int = 720,
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

    sample_count = max(1, min(int(num_frames), frame_count))
    times = np.linspace(start, end, num=sample_count, endpoint=True)
    urls: list[str] = []
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
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            continue
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        urls.append(f"data:image/jpeg;base64,{b64}")
        timestamps.append(float(frame_idx / fps))

    cap.release()
    if not urls:
        raise RuntimeError(f"Failed to decode frames from: {path}")
    return SampledFrames(urls=urls, timestamps=timestamps, duration=float(duration))


def call_api_messages(
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    base_url: str = "",
    proxy: str | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> tuple[Any, str | None]:
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError("The 'openai' package is required. Install with 'pip install openai'.") from e

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy for API calls: {proxy}")

    client = OpenAI(api_key=api_key, base_url=base_url or None)
    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    resp = client.chat.completions.create(**kwargs)
    if not resp.choices:
        return str(resp), None
    choice = resp.choices[0]
    return choice.message, choice.finish_reason


def format_options(item: dict[str, Any]) -> str:
    options = []
    for i, letter in enumerate(LETTERS):
        choice_key = f"answer_choice_{i}"
        if choice_key in item:
            options.append(f"{letter}: {item[choice_key]}")
    return ", ".join(options)


def build_content(prompt: str, image_urls: list[str]) -> list[dict[str, Any]]:
    parts = [{"type": "image_url", "image_url": {"url": url}} for url in image_urls]
    parts.append({"type": "text", "text": prompt})
    return parts


def build_initial_prompt(
    item: dict[str, Any],
    options_str: str,
    duration: float,
    frame_times: list[float],
    video_file: str,
) -> str:
    return (
        "You are a video reasoning agent evaluating a multiple-choice PerceptionComp question.\n"
        f"Video duration: {duration:.2f} seconds.\n"
        "The attached frames are sparsely sampled from the entire video.\n"
        f"Sampled frame timestamps: {', '.join(f'{t:.2f}s' for t in frame_times)}.\n"
        f"The Video path for this video is: {video_file}\n\n"
        f"Question: {item.get('question')}\n"
        f"Options: {options_str}\n\n"
        f"{TOOL_PROMPT}\n"
        "If the API does not support structured tool calls, use this fallback inspection format exactly:\n"
        "<think>brief reasoning about what evidence is missing</think>\n"
        "<inspect>{\"start_time\": 0.0, \"end_time\": 10.0, \"reason\": \"why this clip matters\"}</inspect>"
    )


def build_tool_observation_content(
    image_urls: list[str],
    timestamps: list[float],
    window: dict[str, Any],
) -> list[dict[str, Any]]:
    text = (
        f"Cropped {window['start_time']:.2f}s-{window['end_time']:.2f}s, got {len(image_urls)} frames. "
        f"Frame timestamps: {', '.join(f'{t:.2f}s' for t in timestamps)}."
    )
    return build_content(text, image_urls)


def assistant_message_to_dict(message: Any) -> dict[str, Any]:
    tool_calls = getattr(message, "tool_calls", None)
    content = getattr(message, "content", None) or ""
    output = {"role": "assistant", "content": content}
    if tool_calls:
        output["tool_calls"] = [
            {
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in tool_calls
        ]
    return output


def message_text(message: Any) -> str:
    if isinstance(message, str):
        return message
    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content.strip()
    return str(content or "").strip()


def parse_tool_arguments(raw_arguments: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def make_synthetic_tool_call(round_index: int, request: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"fallback_crop_video_{round_index}",
        "type": "function",
        "function": {
            "name": "crop_video",
            "arguments": json.dumps(request, ensure_ascii=False),
        },
    }


def append_tool_result_message(
    messages: list[dict[str, Any]],
    tool_call_id: str,
    content: list[dict[str, Any]],
    use_tool_role: bool,
) -> None:
    if use_tool_role:
        messages.append({"role": "tool", "tool_call_id": tool_call_id, "content": content})
    else:
        messages.append({"role": "user", "content": content})


def downgrade_tool_history_to_plain_chat(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    downgraded = []
    for message in messages:
        clean_message = {k: v for k, v in message.items() if k not in {"tool_calls", "tool_call_id"}}
        if clean_message.get("role") == "tool":
            clean_message["role"] = "user"
        downgraded.append(clean_message)
    return downgraded


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


def run_agentic_prediction(
    api_key: str,
    model_name: str,
    item: dict[str, Any],
    video_file: str,
    base_url: str,
    proxy: str | None,
    rounds: int,
    global_frames: int,
    crop_frames: int,
    min_window_seconds: float,
) -> dict[str, Any]:
    duration = get_video_duration(video_file)
    options_str = format_options(item)
    inspected_windows: list[dict[str, Any]] = []
    round_records: list[dict[str, Any]] = []
    final_response = ""
    use_tool_role = True
    tools_enabled = True
    total_tool_calls = 0

    global_sampled = sample_video_frames(video_file, num_frames=global_frames)
    initial_prompt = build_initial_prompt(
        item=item,
        options_str=options_str,
        duration=duration,
        frame_times=global_sampled.timestamps,
        video_file=video_file,
    )
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": build_content(initial_prompt, global_sampled.urls)}
    ]

    for round_index in range(max(0, rounds) + 1):
        try:
            message, finish_reason = call_api_messages(
                api_key=api_key,
                model=model_name,
                messages=messages,
                base_url=base_url,
                proxy=proxy,
                tools=[CROP_VIDEO_TOOL] if tools_enabled else None,
            )
        except Exception as e:
            if tools_enabled and "tool" in str(e).lower():
                print(f"Warning: API rejected tool calling, falling back to <inspect> protocol: {e}")
                tools_enabled = False
                use_tool_role = False
                messages = downgrade_tool_history_to_plain_chat(messages)
                message, finish_reason = call_api_messages(
                    api_key=api_key,
                    model=model_name,
                    messages=messages,
                    base_url=base_url,
                    proxy=proxy,
                    tools=None,
                )
            else:
                raise
        response = message_text(message)
        final_response = response
        tool_calls = list(getattr(message, "tool_calls", None) or [])
        messages.append(assistant_message_to_dict(message))

        raw_inspect = extract_inspect_request(response)
        answer, thinking = parse_prediction(response)
        if (tool_calls or raw_inspect is not None) and not has_explicit_answer(response):
            answer = "WRONG"

        tool_results: list[dict[str, Any]] = []
        if tool_calls:
            remaining_tool_budget = max(0, rounds) - total_tool_calls
            for tool_call in tool_calls[: min(MAX_TOOL_CALLS_PER_TURN, remaining_tool_budget)]:
                func_name = tool_call.function.name
                func_args = parse_tool_arguments(tool_call.function.arguments)
                normalized_inspect = (
                    normalize_inspect_request(func_args, duration, min_window_seconds)
                    if func_name == "crop_video" and func_args
                    else None
                )
                if normalized_inspect is None:
                    append_tool_result_message(
                        messages,
                        tool_call.id,
                        [{"type": "text", "text": f"Invalid or unsupported tool call: {func_name}({func_args})"}],
                        use_tool_role=use_tool_role,
                    )
                    tool_results.append(
                        {
                            "name": func_name,
                            "arguments": func_args,
                            "error": "invalid or unsupported tool call",
                        }
                    )
                    continue

                total_tool_calls += 1
                sampled = sample_video_frames(
                    video_file,
                    num_frames=crop_frames,
                    start_time=normalized_inspect["start_time"],
                    end_time=normalized_inspect["end_time"],
                )
                inspected_windows.append(normalized_inspect)
                observation = build_tool_observation_content(
                    sampled.urls,
                    sampled.timestamps,
                    normalized_inspect,
                )
                append_tool_result_message(
                    messages,
                    tool_call.id,
                    observation,
                    use_tool_role=use_tool_role,
                )
                tool_results.append(
                    {
                        "name": func_name,
                        "arguments": func_args,
                        "normalized_window": normalized_inspect,
                        "frame_count": len(sampled.urls),
                        "frame_timestamps": sampled.timestamps,
                    }
                )
        elif raw_inspect is not None and not has_explicit_answer(response):
            normalized_inspect = normalize_inspect_request(raw_inspect, duration, min_window_seconds)
            if normalized_inspect is not None and total_tool_calls < max(0, rounds):
                total_tool_calls += 1
                sampled = sample_video_frames(
                    video_file,
                    num_frames=crop_frames,
                    start_time=normalized_inspect["start_time"],
                    end_time=normalized_inspect["end_time"],
                )
                inspected_windows.append(normalized_inspect)
                synthetic_tool_call = make_synthetic_tool_call(round_index + 1, normalized_inspect)
                append_tool_result_message(
                    messages,
                    synthetic_tool_call["id"],
                    build_tool_observation_content(sampled.urls, sampled.timestamps, normalized_inspect),
                    use_tool_role=False,
                )
                tool_results.append(
                    {
                        "name": "crop_video",
                        "arguments": raw_inspect,
                        "normalized_window": normalized_inspect,
                        "frame_count": len(sampled.urls),
                        "frame_timestamps": sampled.timestamps,
                        "fallback_inspect_protocol": True,
                    }
                )

        round_records.append(
            {
                "round": round_index + 1,
                "finish_reason": finish_reason,
                "raw_response": response,
                "parsed_answer": answer,
                "thinking": thinking,
                "tool_calls": tool_results,
                "message_count_after_round": len(messages),
                "total_tool_calls_after_round": total_tool_calls,
            }
        )

        if answer != "WRONG":
            break
        if round_index >= max(0, rounds):
            break
        if not tool_results:
            break

    predicted, thinking = parse_prediction(final_response)
    if (getattr(message, "tool_calls", None) or extract_inspect_request(final_response) is not None) and not has_explicit_answer(
        final_response
    ):
        predicted = "WRONG"
    return {
        "predicted": predicted,
        "thinking": thinking,
        "raw_response": final_response,
        "rounds": round_records,
        "inspected_windows": inspected_windows,
        "video_duration": duration,
        "message_count": len(messages),
        "total_tool_calls": total_tool_calls,
        "initial_frame_timestamps": global_sampled.timestamps,
    }


def evaluate(
    video_path: str,
    json_file_path: str,
    output_path: str,
    model_name: str,
    api_key: str,
    base_url: str = "",
    proxy: str | None = None,
    rounds: int = 5,
    global_frames: int = 32,
    crop_frames: int = 32,
    min_window_seconds: float = 2.0,
):
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
    json_file_output = os.path.join(output_path, f"Results-{model_name}-agentic.json")

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

    for item in progress(data):
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
                base_url=base_url,
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
                "total_tool_calls": prediction.get("total_tool_calls"),
                "initial_frame_timestamps": prediction.get("initial_frame_timestamps"),
                "agentic_config": {
                    "max_rounds": rounds,
                    "global_frames": global_frames,
                    "crop_frames": crop_frames,
                    "min_window_seconds": min_window_seconds,
                },
            }
        )

        with open(json_file_output, "w", encoding="utf-8") as f:
            json.dump(output_records, f, indent=2, ensure_ascii=False)

    accuracies = {
        cat: (correct_counts[cat] / total_counts[cat] if total_counts[cat] > 0 else 0)
        for cat in categories
    }
    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    overall_accuracy = total_correct / total_questions if total_questions > 0 else 0

    csv_file = os.path.join(output_path, f"Results-{model_name}-agentic.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = list(categories) + ["Overall Accuracy", "Total Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        row = {cat: f"{accuracies.get(cat, 0):.3f}" for cat in categories}
        row["Overall Accuracy"] = f"{overall_accuracy:.3f}"
        row["Total Questions"] = str(total_questions)
        writer.writerow(row)

    print("\nAgentic evaluation complete!")
    print(f"Overall Accuracy: {overall_accuracy:.3f}")
    print(f"Total Questions: {total_questions}")
    print(f"Results: {json_file_output}")
