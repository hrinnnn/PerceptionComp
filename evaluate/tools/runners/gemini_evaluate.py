import os
import json
from tqdm import tqdm
import time
import csv
from collections import defaultdict
import re
import argparse

import google.genai as genai
from google.genai import types


SAFETY_SETTINGS = [
    types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
    types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
]


def chat_with_multi_modal(
    client: genai.Client,
    model: str,
    prompt: str,
    video_file,
    force_thinking: bool = False,
    max_retries: int = 1,
):
    all_responses = []

    ret = client.models.generate_content(
        model=model,
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
    )
    text = ret.text or ""
    all_responses.append(text)

    # If force_thinking is requested and response doesn't include <think>, retry with a clear follow-up
    if force_thinking:
        has_think = bool(re.search(r"<think>", text, re.IGNORECASE))
        retries = 0
        while (not has_think) and retries < max_retries:
            retries += 1
            follow_up = (
                "Please provide your reasoning between <think> and </think> tags, "
                "and then give your final answer between <answer> and </answer> tags. (Only a capital letter, not the full choice) "
                "Only include the reasoning and the final answer in your reply."
            )
            ret2 = client.models.generate_content(
                model=model,
                contents=[video_file, follow_up],
                config=types.GenerateContentConfig(safety_settings=SAFETY_SETTINGS),
            )
            text2 = ret2.text or ""
            all_responses.append(text2)
            if bool(re.search(r"<think>", text2, re.IGNORECASE)):
                text = text2
                break
            text = text + "\n\n" + text2
            has_think = bool(re.search(r"<think>", text, re.IGNORECASE))

    return text, all_responses


def upload_video(api_key: str, local_file_path: str, proxy: str | None = None):
    """Upload a video file and wait until processing completes.

    Returns the uploaded file object from client.files.upload.
    """
    client = genai.Client(api_key=api_key)

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy for upload: {proxy}")

    # Check if file already exists
    file_name = os.path.basename(local_file_path)
    try:
        for cloud_file in client.files.list():
            display_name = getattr(cloud_file, "display_name", "") or getattr(cloud_file, "name", "")
            if display_name.endswith(file_name) or file_name in display_name:
                print(f"Found existing cloud file: {getattr(cloud_file, 'uri', cloud_file.name)}")
                return cloud_file
    except Exception as e:
        print(f"Error listing cloud files: {e}")

    print(f"Uploading file: {local_file_path}")
    video_file = client.files.upload(path=local_file_path)

    while video_file.state == types.FileState.PROCESSING:
        print(".", end="", flush=True)
        time.sleep(5)
        video_file = client.files.get(name=video_file.name)

    if video_file.state == types.FileState.FAILED:
        raise RuntimeError(f"Failed to upload file: {video_file.state}")

    print(f" Completed upload: {video_file.uri}")
    return video_file


def predict_gemini(
    api_key,
    model_name,
    query,
    dst,
    proxy=None,
    force_thinking: bool = False,
    video_file=None,
):
    client = genai.Client(api_key=api_key)

    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy: {proxy}")

    # If caller provided an already-uploaded video_file object, reuse it.
    if video_file is None:
        local_file_path = dst
        video_file = upload_video(api_key, local_file_path, proxy)
    else:
        try:
            print(f"Using cached upload: {video_file.uri}")
        except Exception:
            print("Using cached upload object")

    response, all_responses = chat_with_multi_modal(
        client, model_name, query, video_file, force_thinking=force_thinking, max_retries=1
    )

    return response, all_responses


def evaluate(
    video_path,
    json_file_path,
    output_path,
    model_name,
    api_key,
    proxy=None,
    force_thinking: bool = False,
):
    if "gemini" not in model_name:
        raise ValueError("Only Gemini model is supported")

    os.makedirs(output_path, exist_ok=True)
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)

    output_process = []
    json_file_output = os.path.join(output_path, f"Results-{model_name}.json")

    general_qid_dict = {}
    if os.path.exists(json_file_output):
        try:
            with open(json_file_output, "r", encoding="utf-8") as f:
                content = f.read()
                if content and content.strip():
                    output_process = json.loads(content)
                else:
                    output_process = []
        except Exception as e:
            print(f"Warning: failed to load existing results file '{json_file_output}': {e}")
            try:
                ts = int(time.time())
                backup_path = json_file_output + f".broken.{ts}"
                with open(json_file_output, "r", encoding="utf-8") as fr:
                    orig = fr.read()
                with open(backup_path, "w", encoding="utf-8") as fb:
                    fb.write(orig)
                print(f"Backed up broken JSON to: {backup_path}")

                repaired = re.sub(r",\s*(\]|\})", r"\1", orig)
                output_process = json.loads(repaired)

                with open(json_file_output, "w", encoding="utf-8") as fw:
                    json.dump(output_process, fw, indent=2, ensure_ascii=False)
                print(f"Repaired results file and wrote cleaned JSON to '{json_file_output}'")
            except Exception as e2:
                print(f"Auto-repair failed: {e2}. Starting with empty results.")
                output_process = []

        for item in output_process:
            question_id = item.get("key")
            if question_id:
                general_qid_dict[question_id] = 1

    uploaded_cache = {}

    for item in tqdm(data):
        key = item.get("key")
        if len(output_process) > 0 and key in general_qid_dict:
            print(f"Skipping already processed: {key}")
            continue

        video_id = item.get("video_id")
        question = item.get("question")
        options = []
        for i in range(5):
            choice_key = f"answer_choice_{i}"
            if choice_key in item:
                options.append(f"{chr(65+i)}: {item[choice_key]}")
        options_str = ", ".join(options)
        correct_answer = chr(65 + item.get("answer_id", 0))
        category = item.get("category", "Unknown")

        video = os.path.join(video_path, f"{video_id}.mp4")

        if video not in uploaded_cache:
            try:
                uploaded_cache[video] = upload_video(api_key, video, proxy)
            except Exception as e:
                print(f"Error uploading {video}: {e}")
                raw_response = f"ERROR UPLOADING: {e}"
                all_responses = [raw_response]
                thinking = raw_response.strip()
                output_process.append(
                    {
                        "key": key,
                        "video_id": video_id,
                        "Question": question,
                        "Options": options_str,
                        "GT": correct_answer,
                        "Predicted Answer": "WRONG",
                        "Thinking": thinking,
                        "All Responses": all_responses,
                        "Correct": False,
                        "Category": category,
                    }
                )
                with open(json_file_output, "w", encoding="utf-8") as f:
                    json.dump(output_process, f, indent=2, ensure_ascii=False)
                continue

        question_prompt = (
            f"Based on the given video, reason and answer the single-choice question. "
            f"Provide your reasoning between the <think> and </think> tags, and then give your final answer "
            f"between the <answer> and </answer> tags. The question is: {question}. "
            f"The options are: {options_str}. Your answer:"
        )

        try:
            raw_response, all_responses = predict_gemini(
                api_key,
                model_name,
                question_prompt,
                video,
                proxy,
                force_thinking=force_thinking,
                video_file=uploaded_cache.get(video),
            )
        except Exception as e:
            print(f"Error predicting for {key}: {e}")
            raw_response = f"ERROR: {e}"
            all_responses = [raw_response]

        print(raw_response)
        thinking = raw_response.strip()

        think_pattern = r"<think>\s*(.*?)\s*</think>"
        try:
            matches = re.findall(think_pattern, raw_response, re.DOTALL)
        except:
            matches = []
        if matches:
            thinking = matches[-1].strip()

        pattern = r"<answer>\s*(.*?)\s*</answer>"
        try:
            matches = re.findall(pattern, raw_response, re.DOTALL)
        except:
            matches = []
        if matches:
            choice = matches[-1].strip()
        else:
            choice = None
            m = re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE)
            if m:
                choice = m.group(1)
            else:
                m2 = re.findall(r"\b([A-E])\b", raw_response)
                if m2:
                    choice = m2[-1]
            if not choice:
                choice = raw_response

        if "A" in choice.upper():
            predicted_answer = "A"
        elif "B" in choice.upper():
            predicted_answer = "B"
        elif "C" in choice.upper():
            predicted_answer = "C"
        elif "D" in choice.upper():
            predicted_answer = "D"
        elif "E" in choice.upper():
            predicted_answer = "E"
        else:
            predicted_answer = "WRONG"

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
                "All Responses": all_responses,
                "Correct": predicted_answer == correct_answer,
                "Category": category,
            }
        )

        with open(json_file_output, "w", encoding="utf-8") as f:
            json.dump(output_process, f, indent=2, ensure_ascii=False)

    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    overall_accuracy = total_correct / total_questions if total_questions > 0 else 0

    csv_file = os.path.join(output_path, f"Results-{model_name}.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["Overall Accuracy", "Total Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        row = {"Overall Accuracy": f"{overall_accuracy:.2f}", "Total Questions": str(total_questions)}
        writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gemini model for video QA")
    parser.add_argument("--model_name", default="gemini-2.5-flash", type=str, help="Gemini model name")
    parser.add_argument("--api_key", default=None, type=str, help="Google API key")
    parser.add_argument("--video_path", default="", type=str, help="Path to video files")
    parser.add_argument("--json_file", default="", type=str, help="Path to test JSON")
    parser.add_argument("--output_path", default="", type=str, help="Output directory")
    parser.add_argument("--proxy", default="", type=str, help="Proxy URL")
    parser.add_argument("--force_thinking", action="store_true", help="Retry to force <think> tags when missing")
    args = parser.parse_args()
    evaluate(
        args.video_path,
        args.json_file,
        args.output_path,
        args.model_name,
        args.api_key,
        args.proxy,
        force_thinking=args.force_thinking,
    )
