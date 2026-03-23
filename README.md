# PerceptionComp

PerceptionComp is a benchmark for complex perception-centric video reasoning. It targets questions that cannot be solved from a single frame, a single moment, or a short caption: models must revisit visually complex videos, gather evidence from temporally separated segments, and combine multiple perceptual constraints before answering.

Dataset: <https://huggingface.co/datasets/hrinnnn/PerceptionComp/tree/main>

## Highlights

- Complex perception-centric reasoning instead of caption-level shortcut solving.
- 1,114 manually annotated five-choice questions.
- Seven categories spanning outdoor tour, shopping, sport, variety show, home tour, game, and movie.
- Unified workflow for download -> local video storage -> evaluation.
- Extensible evaluation entry point that supports OpenAI-compatible APIs, Gemini, and custom model runners.

## News

- Added a unified `evaluate/evaluate.py` entry point.
- Added `scripts/download_data.py` for downloading videos from Hugging Face.
- Added a custom runner template for plugging in your own model.

## Leaderboard

The README homepage only shows the overall scores. More detailed per-category and per-difficulty analysis can live in the paper, supplementary materials, or a separate leaderboard page.

### Human Performance

| Model | Overall |
| --- | ---: |
| Expert (unrestricted rewatch) | 100.00 |
| Human | 85.10 |
| Single-view Human (no rewatch) | 18.97 |

### Proprietary Models

| Model | Overall |
| --- | ---: |
| Gemini-3-Flash | 45.96 |
| Gemini-3-Pro | 44.43 |
| Gemini-2.5-Pro | 44.34 |
| Seed-2.0-Pro | 44.34 |
| GPT-o3 | 43.54 |
| GPT-5.2 | 40.75 |
| Gemini-2.5-Flash | 38.15 |
| GPT-5 | 36.45 |
| GPT-4.1 | 34.02 |
| GPT-4o-latest | 32.50 |

### Open-Source Instruct Models

| Model | Overall |
| --- | ---: |
| Qwen2.5-VL 7B | 22.73 |
| InternVL-3.5 8B | 32.32 |
| Qwen3-VL 8B | 34.06 |
| Qwen3-VL 30B | 34.38 |
| Qwen2.5-VL 72B | 31.33 |
| GLM-4.5V 106B | 36.69 |
| Qwen3-VL 235B | 34.02 |

### Open-Source Thinking Models

| Model | Overall |
| --- | ---: |
| Video-R1 7B | 26.27 |
| VideoChat-R1 7B | 28.63 |
| Qwen3-VL-Thinking 8B | 33.82 |
| Qwen3-VL-Thinking 30B | 35.68 |
| Qwen3-VL-Thinking 235B | 38.20 |

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

## Data Release

PerceptionComp is released in two parts:

1. GitHub repository:
   contains benchmark annotations, evaluation code, runner templates, analysis utilities, and documentation.
2. Hugging Face dataset:
   stores the benchmark videos referenced by `video_id`.

Current release structure:

- benchmark annotations:
  [1-1114.json](/Users/zhaozhixuan/Desktop/tsinghua_learning/大二暑/暑研/PerceptionComp/benchmark/annotations/official/1-1114.json)
- video host:
  <https://huggingface.co/datasets/hrinnnn/PerceptionComp/tree/main>
- local video target directory:
  [benchmark/videos](/Users/zhaozhixuan/Desktop/tsinghua_learning/大二暑/暑研/PerceptionComp/benchmark/videos)

This split release strategy is standard for video benchmarks because the benchmark code should stay lightweight while the video assets are distributed through a data host.

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

The default custom runner template is now a near-runnable local `transformers` scaffold. If your model follows a Hugging Face VLM workflow, you can often start from the template directly instead of writing a runner from scratch.

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

## Evaluation Protocol

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

In the current repository snapshot, the evaluation protocol is:

1. Load the official annotation file.
2. Map each `video_id` to a local video file under `benchmark/videos/`.
3. Build a standardized multiple-choice prompt.
4. Run inference through one of the supported backends.
5. Parse the model output into one final answer among `A/B/C/D/E`.
6. Compute exact-match accuracy.
7. Save per-question outputs and aggregate metrics.

To keep results comparable, external model integrations should not modify:

- the annotation file,
- the prompt structure,
- the answer parser,
- the metric definition,
- the output schema.

Only the model-side inference path should change.

## FAQ

### Why are videos hosted on Hugging Face instead of in the Git repository?

Because video benchmarks are large. A standard public benchmark setup keeps code and annotations in Git, while large video assets are hosted on a dataset platform.

### Can I run PerceptionComp on my own model?

Yes. If your model supports an OpenAI-compatible API, use `--provider api`. If it is a Gemini model, use `--provider gemini`. Otherwise, use `--provider custom` and implement a model adapter with the provided template.

### What if my model is local and not exposed as an API?

Use the custom runner path. The default template now includes a near-runnable local `transformers` example based on frame sampling plus Hugging Face VLM inference.

### Do I need to change the benchmark code to evaluate my own model?

Usually no. You should only change the model adapter. The benchmark-side protocol should remain fixed.

### Why do some leaderboard entries have different numbers of answered questions?

Because the current repository stores historical result files from different evaluation stages. The README leaderboard is a repository snapshot, not yet a fully standardized official leaderboard.

### Can I evaluate on a different split or a custom annotation file?

Yes. Pass `--annotations PATH_TO_JSON` to `evaluate/evaluate.py`.

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
