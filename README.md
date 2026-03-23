# PerceptionComp

PerceptionComp is a benchmark for complex perception-centric video reasoning. It targets questions that cannot be solved from a single frame, a single moment, or a short caption: models must revisit visually complex videos, gather evidence from temporally separated segments, and combine multiple perceptual constraints before answering.

Dataset: <https://huggingface.co/datasets/hrinnnn/PerceptionComp/tree/main>

## Highlights

- Complex perception-centric reasoning instead of caption-level shortcut solving.
- 1,114 manually annotated five-choice questions.
- 273 unique `video_id` instances in the current official release file.
- Seven categories spanning outdoor tour, shopping, sport, variety show, home tour, game, and movie.
- Unified workflow for download -> local video storage -> evaluation.
- Extensible evaluation entry point that supports OpenAI-compatible APIs, Gemini, and custom model runners.

## News

- Added a unified `evaluate/evaluate.py` entry point.
- Added `scripts/download_data.py` for downloading videos from Hugging Face.
- Added a custom runner template for plugging in your own model.

## Leaderboard

The table below is a lightweight snapshot of result files currently stored in `evaluate/results/`. These runs do not all cover the same number of answered questions, so this should be read as a repository snapshot rather than a strict official leaderboard.

| Model | Backend | Answered Questions | Accuracy |
| --- | --- | ---: | ---: |
| Gemini-2.5-Pro | Gemini | 500 | 98.80% |
| Gemini-3-Pro-Preview | Gemini | 500 | 99.00% |
| Gemini-3.1-Pro-Preview | Gemini | 500 | 97.40% |
| Gemini-2.5-Flash | Gemini | 500 | 85.00% |
| Doubao-Seed-2.0-Pro | API | 614 | 80.46% |
| GPT-o3 | API | 614 | 44.14% |
| GPT-5 | API | 614 | 42.83% |
| GPT-5.2 | API | 1114 | 40.75% |
| GPT-4.1 | API | 614 | 40.55% |
| Qwen3-VL-235B-A22B-Thinking | API | 1110 | 38.20% |
| GLM-4.5V | API | 1101 | 36.69% |
| Qwen3-VL-30B-A3B-Thinking | API | 1110 | 35.68% |
| Qwen3-VL-30B-A3B-Instruct | API | 1111 | 34.38% |
| GPT-4o | API | 614 | 34.36% |
| Qwen3-VL-235B-A22B-Instruct | API | 1111 | 34.02% |
| Qwen2.5-VL-72B-Instruct | API | 614 | 31.76% |
| Qwen2.5-VL-7B-Instruct | API | 614 | 21.01% |

Note: some historical result files in this repository are partial, experimental, or otherwise not directly comparable. A stricter official leaderboard can be added later after evaluation settings are fully standardized.

## Quick Start

This section is intentionally step-by-step. The expected workflow is:

1. Clone the repository.
2. Install dependencies.
3. Download the benchmark videos from Hugging Face.
4. Run evaluation with a built-in backend or your own model adapter.
5. Read the generated result files from `evaluate/results/`.

### Step 1. Clone the Repository

```bash
git clone YOUR_REPO_URL
cd PerceptionComp
```

### Step 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3. Download the Benchmark Videos

Download all benchmark videos into `benchmark/videos/`:

```bash
python scripts/download_data.py --repo-id hrinnnn/PerceptionComp
```

If the Hugging Face dataset requires authentication:

```bash
python scripts/download_data.py \
  --repo-id hrinnnn/PerceptionComp \
  --hf-token YOUR_HF_TOKEN
```

Expected local layout after download:

```text
benchmark/videos/<video_id>.mp4
```

### Step 4. Run Evaluation with a Built-in Backend

PerceptionComp currently supports three evaluation modes:

- `api`: OpenAI-compatible APIs
- `gemini`: Gemini video-upload workflow
- `custom`: your own model runner

#### Option A. OpenAI-Compatible API

Use this for GPT-style APIs, Qwen API deployments, GLM-compatible endpoints, Doubao-style endpoints, and similar services.

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

Optional arguments:

- `--annotations`: use a different annotation file
- `--output-dir`: change where results are written
- `--frames`: control the number of sampled frames
- `--proxy`: pass a proxy for API calls

#### Option B. Gemini

```bash
python evaluate/evaluate.py \
  --model YOUR_GEMINI_MODEL_NAME \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

Optional arguments:

- `--force-thinking`: retry when `<think>` tags are missing
- `--annotations`: use a different annotation file
- `--output-dir`: change where results are written

### Step 5. Check the Outputs

Evaluation outputs are written to:

```text
evaluate/results/Results-<model>.json
evaluate/results/Results-<model>.csv
```

The JSON file stores per-question predictions and raw responses. The CSV file stores aggregated scores.

## Evaluate Your Own Model

Yes, a public benchmark should support evaluation on external models. This is standard practice for benchmark repositories, but different projects implement it differently:

- LongVideoBench provides a dataset loader and encourages integration into a general evaluation framework.
- Video-Holmes exposes model-specific hooks inside the evaluation pipeline and documents where to modify the model code.

PerceptionComp follows the same general principle:

- the benchmark owns the dataset, prompt construction, answer parsing, metrics, and output format;
- your model adapter only needs to turn `(video, prompt)` into a raw text response.

That separation is what makes a benchmark portable across proprietary APIs, local checkpoints, internal inference servers, and future evaluation frameworks. Source: [LongVideoBench README](https://github.com/longvideobench/LongVideoBench), [Video-Holmes README](https://github.com/TencentARC/Video-Holmes).

### Option 1. Your Model Already Supports an OpenAI-Compatible API

If your model is already exposed through an OpenAI-compatible endpoint, you do not need to write any adapter. Just use:

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

### Option 2. Your Model Is a Gemini Model

If your model is part of the Gemini family, use:

```bash
python evaluate/evaluate.py \
  --model YOUR_GEMINI_MODEL_NAME \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

### Option 3. Your Model Needs Custom Inference Logic

If your model is local, served by an internal API, or uses a different SDK / pipeline, implement a custom runner.

#### Step 1. Copy the Template

```bash
cp evaluate/tools/runners/custom_template.py evaluate/tools/runners/my_model.py
```

#### Step 2. Implement the Model Hook

Open `evaluate/tools/runners/my_model.py` and replace `run_your_model(...)` with your own inference logic.

Your function should take:

- `video_path`
- `prompt`
- `model_name`
- optional `custom_config`

and return:

- a raw string response from the model

The simplest recommended output format is:

```text
Answer: A
```

or, if your model supports reasoning traces:

```text
<think>
your reasoning here
</think>
<answer>
A
</answer>
```

#### Step 3. Run Evaluation with the Custom Runner

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider custom \
  --custom-runner evaluate/tools/runners/my_model.py \
  --video-dir benchmark/videos
```

If your runner needs an extra config file:

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider custom \
  --custom-runner evaluate/tools/runners/my_model.py \
  --custom-config path/to/your_config.json \
  --video-dir benchmark/videos
```

#### Step 4. Keep the Benchmark Protocol Fixed

When adapting your own model, do not modify:

- the annotation format,
- the question prompt structure,
- the answer parsing logic,
- the metric computation,
- the output schema.

Only change the model-side inference path. That is what keeps your results comparable to other models.

For a more explicit implementation guide, see [bring_your_own_model.md](/Users/zhaozhixuan/Desktop/tsinghua_learning/大二暑/暑研/PerceptionComp/docs/bring_your_own_model.md).

## Supported Models

The unified entry point currently supports two built-in backend families plus a custom adapter path:

| Backend | Usage | Notes |
| --- | --- | --- |
| OpenAI-compatible API | `--provider api` | Works for GPT-style APIs, Qwen API deployments, GLM-compatible endpoints, Doubao-style endpoints, and other OpenAI-compatible services. |
| Gemini | `--provider gemini` | Uses the Gemini video upload workflow for Gemini-family models. |
| Custom runner | `--provider custom` | Loads a Python file that implements your own inference logic. |

Models already represented in the repository's archived results include:

- GPT-4.1, GPT-4o, GPT-5, GPT-5.2, o3
- Gemini-2.5-Flash, Gemini-2.5-Pro, Gemini-3-Pro, Gemini-3.1-Pro
- Qwen2.5-VL-7B, Qwen2.5-VL-72B
- Qwen3-VL-235B-A22B-Instruct, Qwen3-VL-235B-A22B-Thinking
- Qwen3-VL-30B-A3B-Instruct, Qwen3-VL-30B-A3B-Thinking
- GLM-4.5V
- Doubao-Seed variants

## Benchmark Snapshot

| Item | Value |
| --- | --- |
| Official annotation file | `benchmark/annotations/official/1-1114.json` |
| Questions | 1,114 |
| Unique `video_id` values in the official annotation file | 273 |
| Question format | 5-choice multiple choice |
| Categories | 7 |

Current category counts in the official annotation file:

| Category | Questions |
| --- | --- |
| outdoor tour | 391 |
| shopping | 197 |
| sport | 193 |
| variety show | 149 |
| home tour | 128 |
| game | 31 |
| movie | 25 |

## Repository Layout

```text
.
├── benchmark/
│   ├── annotations/
│   │   ├── official/
│   │   ├── splits/
│   │   ├── legacy/
│   │   └── archive/
│   ├── assets/
│   └── videos/
├── docs/
│   └── bring_your_own_model.md
├── evaluate/
│   ├── evaluate.py
│   ├── results/
│   └── tools/
├── scripts/
│   └── download_data.py
├── requirements.txt
└── README.md
```

## Annotation Format

Each item in the official benchmark file is a five-choice question tied to a `video_id`.

Core fields:

- `key`: question id
- `video_id`: video name without `.mp4`
- `question`: question text
- `answer_choice_0` to `answer_choice_4`: the five answer options
- `answer_id`: zero-based correct option index
- `answer`: text form of the correct answer
- `category`: semantic category
- `difficulty`: difficulty label

See [schema.md](/Users/zhaozhixuan/Desktop/tsinghua_learning/大二暑/暑研/PerceptionComp/benchmark/annotations/schema.md) for the compact schema reference.

## Evaluation Design

The benchmark side should own:

- dataset loading,
- prompt construction,
- answer parsing,
- metric computation,
- result serialization.

The model side should only own:

- how to prepare the video input,
- how to call the model,
- how to return a raw text response.

This separation is what makes a benchmark portable across proprietary APIs, local checkpoints, and future evaluation frameworks. It is also the main thing you should preserve as PerceptionComp grows.

## Contact

If you want to report an issue, suggest improvements, or discuss evaluation of a new model family, please open an issue in this repository first.

## License

License and data usage terms should be added before broader public release. At minimum, the repository should clearly separate:

- code license,
- dataset usage policy,
- video copyright statement,
- contact path for takedown requests.

## Citation

If you use PerceptionComp, please cite the corresponding paper once the public version is finalized.

```bibtex
@misc{perceptioncomp2026,
  title={PerceptionComp: A Video Benchmark for Complex Perception-Centric Reasoning},
  year={2026}
}
```
