import os
import json
from tqdm import tqdm
import time
import random
import csv
from collections import defaultdict
import math
import numpy as np
import re
import argparse


def chat_with_multi_modal(
    model: str,
    prompt: str,
    video_file,
    force_thinking: bool = False,
    max_retries: int = 1,
):
    import google.generativeai as genai

    safety_settings = {
        "HATE": "BLOCK_NONE",
        "HARASSMENT": "BLOCK_NONE",
        "SEXUAL": "BLOCK_NONE",
        "DANGEROUS": "BLOCK_NONE",
    }

    model = genai.GenerativeModel(model_name=model)
    request_options = {"timeout": 600}

    all_responses = []

    ret = model.generate_content(
        [video_file, prompt],
        request_options=request_options,
        safety_settings=safety_settings,
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
                "and then give your final answer between <answer> and </answer> tags. "
                "Only include the reasoning and the final answer in your reply."
            )
            ret2 = model.generate_content(
                [video_file, follow_up],
                request_options=request_options,
                safety_settings=safety_settings,
            )
            text2 = ret2.text or ""
            all_responses.append(text2)
            if bool(re.search(r"<think>", text2, re.IGNORECASE)):
                text = text2
                break
            text = text + "\n\n" + text2
            has_think = bool(re.search(r"<think>", text, re.IGNORECASE))

    return text, all_responses


def get_remote_file_by_path(api_key, local_file_path, proxy=None):
    """Check if file already exists on cloud, return it if found, otherwise return None."""
    import google.generativeai as genai
    
    genai.configure(api_key=api_key)
    
    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
    
    file_name = os.path.basename(local_file_path)
    
    try:
        # List all files on the cloud
        for file in genai.list_files():
            # Match by filename
            if file.name.endswith(file_name) or file_name in file.name:
                print(f"Found existing cloud file: {file.uri}")
                return file
    except Exception as e:
        print(f"Error listing cloud files: {e}")
    
    return None


def upload_video(api_key, local_file_path, proxy=None):
    """Upload a video file to the Generative AI service and wait until processing completes.

    Returns the uploaded file object from genai.upload_file.
    """
    import google.generativeai as genai

    genai.configure(api_key=api_key)

    # 设置代理（如果提供）
    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy for upload: {proxy}")

    # 先检查云端是否已存在该文件
    existing_file = get_remote_file_by_path(api_key, local_file_path, proxy)
    if existing_file:
        return existing_file

    print(f"Uploading file: {local_file_path}")
    video_file = genai.upload_file(path=local_file_path)

    while video_file.state.name == "PROCESSING":
        print(".", end="")
        time.sleep(5)
        video_file = genai.get_file(video_file.name)

    if video_file.state.name == "FAILED":
        raise RuntimeError(f"Failed to upload file: {video_file.state.name}")

    print(f"Completed upload: {video_file.uri}")
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
    import google.generativeai as genai

    response = "WRONG"

    genai.configure(api_key=api_key)

    # 设置代理（如果提供）
    if proxy:
        os.environ["HTTPS_PROXY"] = proxy
        os.environ["HTTP_PROXY"] = proxy
        print(f"Using proxy: {proxy}")

    # If caller provided an already-uploaded video_file object, reuse it.
    if video_file is None:
        local_file_path = dst
        # upload and wait
        video_file = upload_video(api_key, local_file_path, proxy)
    else:
        try:
            print(f"Using cached upload: {video_file.uri}")
        except Exception:
            # Fallback if video_file doesn't have uri attribute
            print("Using cached upload object")

    response, all_responses = chat_with_multi_modal(
        model_name, query, video_file, force_thinking=force_thinking, max_retries=1
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
    # 只处理 Gemini
    if "gemini" not in model_name:
        raise ValueError("Only Gemini model is supported")

    os.makedirs(output_path, exist_ok=True)
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 调整问题类型（根据你的数据）
    question_types = []

    correct_counts = defaultdict(int)
    total_counts = defaultdict(int)

    output_process = []
    json_file_output = os.path.join(output_path, f"Results-{model_name}.json")

    general_qid_dict = {}
    if os.path.exists(json_file_output):
        # gracefully handle empty, malformed, or trailing-comma JSON files
        try:
            with open(json_file_output, "r", encoding="utf-8") as f:
                content = f.read()
                if content and content.strip():
                    output_process = json.loads(content)
                else:
                    output_process = []
        except Exception as e:
            print(
                f"Warning: failed to load existing results file '{json_file_output}': {e}"
            )
            # attempt a simple auto-repair for common trailing-comma issues
            try:
                # backup original
                ts = int(time.time())
                backup_path = json_file_output + f".broken.{ts}"
                with open(json_file_output, "r", encoding="utf-8") as fr:
                    orig = fr.read()
                with open(backup_path, "w", encoding="utf-8") as fb:
                    fb.write(orig)
                print(f"Backed up broken JSON to: {backup_path}")

                # remove trailing commas before ] or }
                repaired = re.sub(r",\s*(\]|\})", r"\1", orig)

                # try loading repaired content
                output_process = json.loads(repaired)

                # if succeeded, overwrite the results file with repaired JSON
                with open(json_file_output, "w", encoding="utf-8") as fw:
                    json.dump(output_process, fw, indent=2, ensure_ascii=False)
                print(
                    f"Repaired results file and wrote cleaned JSON to '{json_file_output}'"
                )
            except Exception as e2:
                print(f"Auto-repair failed: {e2}. Starting with empty results.")
                output_process = []

        for item in output_process:
            question_id = item.get("key")  # 使用 key 作为 ID
            if question_id:
                general_qid_dict[question_id] = 1

    # cache for uploaded videos so the same file isn't uploaded multiple times
    uploaded_cache = {}

    for item in tqdm(data):
        key = item.get("key")
        if len(output_process) > 0 and key in general_qid_dict:
            print(f"Skipping already processed: {key}")
            continue

        video_id = item.get("video_id")
        question = item.get("question")
        # 构建选项字符串
        options = []
        for i in range(5):  # 假设最多5个选项
            choice_key = f"answer_choice_{i}"
            if choice_key in item:
                options.append(f"{chr(65+i)}: {item[choice_key]}")  # A, B, C, D, E
        options_str = ", ".join(options)
        correct_answer = chr(65 + item.get("answer_id", 0))  # 转换为 A, B, C 等
        category = item.get("category", "Unknown")

        video = os.path.join(video_path, f"{video_id}.mp4")

        # 上传缓存：相同视频文件只上传一次并复用上传的 file 对象
        if video not in uploaded_cache:
            try:
                uploaded_cache[video] = upload_video(api_key, video, proxy)
            except Exception as e:
                print(f"Error uploading {video}: {e}")
                # continue to next item to avoid breaking the whole run
                raw_response = f"ERROR UPLOADING: {e}"
                all_responses = [raw_response]
                thinking = raw_response.strip()
                predicted_answer = "WRONG"
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
                        "Correct": False,
                        "Category": category,
                    }
                )
                with open(json_file_output, "w", encoding="utf-8") as f:
                    json.dump(output_process, f, indent=2, ensure_ascii=False)
                # skip the rest of processing for this question
                continue

        question_prompt = f"Based on the given video, reason and answer the single-choice question. Provide your reasoning between the <think> and </think> tags, and then give your final answer between the <answer> and </answer> tags. The question is: {question}. The options are: {options_str}. Your answer:"

        # 预测答案（raw_response 保留模型全部输出）
        try:
            # reuse the uploaded file object from cache
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

        # 将模型完整返回保存为 Thinking 内容（始终保存）
        print(raw_response)
        thinking = raw_response.strip()

        # 解析推理和答案（从 raw_response 中解析标签）
        think_pattern = r"<think>\s*(.*?)\s*</think>"
        try:
            matches = re.findall(think_pattern, raw_response, re.DOTALL)
        except:
            matches = []
        if matches:
            # 如果存在 <think> 标签，优先使用最后一个
            thinking = matches[-1].strip()

        pattern = r"<answer>\s*(.*?)\s*</answer>"
        try:
            matches = re.findall(pattern, raw_response, re.DOTALL)
        except:
            matches = []
        if matches:
            choice = matches[-1].strip()
        else:
            # 后备：尝试在原始响应中查找 'Answer: X' 或 A-E
            choice = None
            m = re.search(r"(?:Answer[:\s]*)([A-E])\b", raw_response, re.IGNORECASE)
            if m:
                choice = m.group(1)
            else:
                m2 = re.findall(r"\b([A-E])\b", raw_response)
                if m2:
                    choice = m2[-1]
            if not choice:
                # 如果仍无法解析，保留整个原始响应作为 choice（后续将标为 WRONG）
                choice = raw_response

        # 标准化答案
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

    # 计算准确率
    accuracies = {
        q_type: (
            correct_counts[q_type] / total_counts[q_type]
            if total_counts[q_type] > 0
            else 0
        )
        for q_type in question_types
    }
    total_correct = sum(correct_counts.values())
    total_questions = sum(total_counts.values())
    overall_accuracy = total_correct / total_questions if total_questions > 0 else 0

    csv_file = os.path.join(output_path, f"Results-{model_name}.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = list(question_types) + ["Overall Accuracy", "Total Questions"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        row = {q_type: f"{accuracies.get(q_type, 0):.2f}" for q_type in question_types}
        row["Overall Accuracy"] = f"{overall_accuracy:.2f}"
        row["Total Questions"] = str(total_questions)
        writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Gemini model for video QA")
    parser.add_argument(
        "--model_name", default="gemini-3-flash-preview", type=str, help="Gemini model name"
    )
    parser.add_argument(
        "--api_key",
        default=None,
        type=str,
        help="Google API key",
    )
    parser.add_argument(
        "--video_path",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/videos",
        type=str,
        help="Path to video files",
    )
    parser.add_argument(
        "--json_file",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/summer_ques/4in1.json",
        type=str,
        help="Path to test JSON",
    )
    parser.add_argument(
        "--output_path",
        default="/Users/jadeons/Desktop/project/research/PerceptionComp/PerceptionComp/test_result_summer/gemini_3_flash",
        type=str,
        help="Output directory",
    )
    parser.add_argument(
        "--proxy",
        default="http://127.0.0.1:1082",
        type=str,
        help="Proxy URL",
    )
    parser.add_argument(
        "--force_thinking",
        action="store_true",
        help="If set, retry to force model to output <think> tags when missing",
    )
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
