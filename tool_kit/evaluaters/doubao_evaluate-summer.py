import os
import json
from tqdm import tqdm
import time
import csv
from collections import defaultdict
import numpy as np
import re
import argparse
import base64
import cv2


def sample_video_frames(path: str, num_frames: int = 6, resize=None):
    """Return a list of JPEG data URLs (base64) sampled evenly from the video.

    Requires OpenCV (cv2). If unavailable, raises ImportError with a clear hint.
    """
    try:
        import cv2
    except ImportError as e:
        raise ImportError(
            "OpenCV (cv2) is required to sample frames from video. Please install with 'pip install opencv-python'."
        ) from e

    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    if frame_count <= 0:
        cap.release()
        return []

    idxs = np.linspace(0, frame_count - 1, num=min(num_frames, frame_count), dtype=int)
    urls = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret or frame is None:
            continue
        if resize:
            h, w = frame.shape[:2]
            short_side = min(h, w)
            if short_side > resize:
                scale = resize / short_side
                new_w = int(w * scale)
                new_h = int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h))
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            continue
        b64 = base64.b64encode(buf.tobytes()).decode("utf-8")
        data_url = f"data:image/jpeg;base64,{b64}"
        urls.append(data_url)
    cap.release()
    return urls


def call_doubao(api_key: str, model: str, content_parts, base_url: str = None, proxy: str = None):
    """Call Doubao via OpenAI-compatible API and return raw text response.

    content_parts: list of content parts, e.g., {"type": "image_url", "image_url": {"url": url}} 
                   and {"type": "text", "text": prompt}
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(
            "The 'openai' package is required. Install with 'pip install openai'."
        ) from e

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy for API calls: {proxy}")

    # Set default base_url for Doubao
    if base_url is None:
        base_url = "https://ark.cn-beijing.volces.com/api/v3"

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content_parts}],
            temperature=1,
        )
        
        # Extract the response
        if resp.choices and len(resp.choices) > 0:
            msg = resp.choices[0].message
            if isinstance(msg.content, str):
                return msg.content.strip()
            else:
                return str(msg.content)
        else:
            return str(resp)
    except Exception as e:
        raise Exception(f"Error calling Doubao API: {e}") from e


def predict_doubao(
    api_key: str,
    model_name: str,
    query: str,
    video_path: str,
    base_url: str = None,
    proxy: str = None,
    frames: int = 6,
):
    """Predict using Doubao model with video frames."""
    
    # Extract frames from video
    try:
        image_urls = sample_video_frames(video_path, num_frames=frames, resize=720)
    except Exception as e:
        print(f"Frame extraction failed for {video_path}: {e}")
        raise

    if not image_urls:
        raise ValueError(f"No frames could be extracted from {video_path}")

    # Build content for API call
    content = []
    for url in image_urls:
        content.append({"type": "image_url", "image_url": {"url": url}})
    content.append({"type": "text", "text": query})

    # Call Doubao
    response = call_doubao(api_key, model_name, content, base_url, proxy)
    return response


def evaluate(
    video_path: str,
    json_file_path: str,
    output_path: str,
    model_name: str,
    api_key: str,
    base_url: str = None,
    proxy: str = None,
    frames: int = 6,
):
    """Evaluate video QA using Doubao model."""
    
    if base_url is None:
        base_url = "https://ark.cn-beijing.volces.com/api/v3"

    os.makedirs(output_path, exist_ok=True)
    
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build category list dynamically
    categories = []
    for it in data:
        c = it.get("category", "Unknown")
        if c not in categories:
            categories.append(c)

    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)

    output_process = []
    json_file_output = os.path.join(output_path, f"Results-{model_name}.json")

    # Load previously processed results if they exist
    processed_keys = set()
    if os.path.exists(json_file_output) and os.path.getsize(json_file_output) > 0:
        try:
            with open(json_file_output, "r", encoding="utf-8") as f:
                content = f.read()
                if content and content.strip():
                    output_process = json.loads(content)
                    for item in output_process:
                        qid = item.get("key")
                        if qid:
                            processed_keys.add(qid)
                        # Restore counts from previously processed results
                        cat = item.get("Category", "Unknown")
                        total_counts[cat] += 1
                        if item.get("Correct"):
                            correct_counts[cat] += 1
        except Exception as e:
            print(f"Warning: failed to load existing results file: {e}")
            output_process = []
            processed_keys = set()

    for item in tqdm(data):
        key = item.get("key")
        if key in processed_keys:
            print(f"Skipping already processed: {key}")
            continue

        video_id = item.get("video_id")
        question = item.get("question")
        
        # Build options string
        options = []
        for i in range(5):
            choice_key = f"answer_choice_{i}"
            if choice_key in item:
                options.append(f"{chr(65+i)}: {item[choice_key]}")
        options_str = ", ".join(options)
        correct_answer = chr(65 + item.get("answer_id", 0))
        category = item.get("category", "Unknown")

        video = os.path.join(video_path, f"{video_id}.mp4")
        if not os.path.exists(video):
            print(f"Video not found, skipping: {video}")
            continue

        # Build prompt
        question_prompt = (
            "Based on the given video frames, reason and answer the single-choice question. "
            "Provide your reasoning between the <think> and </think> tags, and then give your final answer "
            "between the <answer> and </answer> tags. "
            "Inside the <answer> and </answer> tags, only provide a single letter (A, B, C, D, or E) corresponding to your choice. "
            f"The question is: {question}. The options are: {options_str}. Your answer:"
        )

        # Predict
        try:
            raw_response = predict_doubao(
                api_key,
                model_name,
                question_prompt,
                video,
                base_url,
                proxy,
                frames,
            )
        except Exception as e:
            print(f"Error predicting for {key}: {e}")
            raw_response = f"ERROR: {e}"

        print(raw_response)
        thinking = raw_response.strip()

        # Parse <think> tags
        think_pattern = r"<think>\s*(.*?)\s*</think>"
        try:
            matches = re.findall(think_pattern, raw_response, re.DOTALL)
            if matches:
                thinking = matches[-1].strip()
        except Exception:
            pass

        # Parse <answer> tags
        pattern = r"<answer>\s*(.*?)\s*</answer>"
        try:
            matches = re.findall(pattern, raw_response, re.DOTALL)
            if matches:
                choice = matches[-1].strip()
            else:
                choice = None
        except Exception:
            choice = None

        # Fallback parsing if <answer> tags not found
        if choice is None:
            m = re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE)
            if m:
                choice = m.group(1)
            else:
                m2 = re.findall(r"\b([A-E])\b", raw_response)
                if m2:
                    choice = m2[-1]
                else:
                    choice = raw_response

        # Normalize predicted answer
        cu = str(choice).strip().upper()
        letter_matches = re.findall(r"\b([A-E])\b", cu)
        if letter_matches:
            predicted_answer = letter_matches[-1]
        else:
            predicted_answer = "WRONG"

        # Update counts
        if predicted_answer == correct_answer:
            correct_counts[category] += 1
        total_counts[category] += 1

        output_process.append(
            {
                "key": key,
                "video_id": video_id,
                "Question": question,
                "Options": options_str,
                "GT": correct_answer,
                "Predicted Answer": predicted_answer,
                "Thinking": thinking,
                "Correct": predicted_answer == correct_answer,
                "Category": category,
                "all_response": raw_response,
            }
        )

        # Save results after each item
        with open(json_file_output, "w", encoding="utf-8") as f:
            json.dump(output_process, f, indent=2, ensure_ascii=False)

    # Calculate accuracies
    accuracies = {
        cat: (correct_counts[cat] / total_counts[cat] if total_counts[cat] > 0 else 0)
        for cat in categories
    }
    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    overall_accuracy = total_correct / total_questions if total_questions > 0 else 0

    # Write CSV results
    csv_file = os.path.join(output_path, f"Results-{model_name}.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = list(categories) + ["Overall Accuracy", "Total Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        row = {cat: f"{accuracies.get(cat, 0):.3f}" for cat in categories}
        row["Overall Accuracy"] = f"{overall_accuracy:.3f}"
        row["Total Questions"] = str(total_questions)
        writer.writerow(row)

    print(f"\nEvaluation complete!")
    print(f"Overall Accuracy: {overall_accuracy:.3f}")
    print(f"Total Questions: {total_questions}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Doubao model for video QA")
    parser.add_argument(
        "--model_name",
        default="doubao-seed-2-0-pro-260215",
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
        default="https://ark.cn-beijing.volces.com/api/v3",
        type=str,
        help="Doubao API base URL",
    )
    parser.add_argument(
        "--video_path",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/videos",
        type=str,
        help="Path to video files",
    )
    parser.add_argument(
        "--json_file",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/summer_ques/1-500.json",
        type=str,
        help="Path to test JSON",
    )
    parser.add_argument(
        "--output_path",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result_summer/doubao",
        type=str,
        help="Output directory",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        type=str,
        help="Proxy URL (optional)",
    )
    parser.add_argument(
        "--frames",
        default=64,
        type=int,
        help="Number of frames to sample per video",
    )
    
    args = parser.parse_args()

    # Get API key from argument or environment variable
    api_key = args.api_key or os.getenv("ARK_API_KEY")
    if not api_key:
        raise ValueError("API key must be provided via --api_key argument or ARK_API_KEY environment variable")

    evaluate(
        args.video_path,
        args.json_file,
        args.output_path,
        args.model_name,
        api_key,
        args.base_url,
        args.proxy,
        args.frames,
    )
