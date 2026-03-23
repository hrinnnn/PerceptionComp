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

## Quick Start

Clone the repository, install dependencies, download the videos, and run evaluation:

```bash
git clone YOUR_REPO_URL
cd PerceptionComp
pip install -r requirements.txt
python scripts/download_data.py --repo-id hrinnnn/PerceptionComp
python evaluate/evaluate.py \
  --model gpt-5.2 \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

If the Hugging Face dataset requires authentication:

```bash
python scripts/download_data.py \
  --repo-id hrinnnn/PerceptionComp \
  --hf-token YOUR_HF_TOKEN
```

Gemini example:

```bash
python evaluate/evaluate.py \
  --model gemini-2.5-flash \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

## Run Your Own Model

Yes, a public benchmark should ideally let other people run their own models on the same data and protocol. In practice, this is usually implemented in one of three ways:

1. Support a standard API format.
2. Integrate into a common evaluation framework.
3. Expose a small adapter interface for custom models.

PerceptionComp currently supports the first and third options directly:

| Mode | How it works | Best for |
| --- | --- | --- |
| `--provider api` | Routes evaluation to an OpenAI-compatible API runner. | GPT-style endpoints, Qwen API deployments, GLM-compatible services, Doubao-style services, and similar endpoints. |
| `--provider gemini` | Routes evaluation to the Gemini video-upload runner. | Gemini-family models. |
| `--provider custom` | Loads a user-specified Python runner file. | Your own local model, internal server, or any model that needs custom inference logic. |

### Custom Model Example

Copy and modify the template runner:

```bash
cp evaluate/tools/runners/custom_template.py evaluate/tools/runners/my_model.py
```

Then implement `run_your_model(...)` in that file, and run:

```bash
python evaluate/evaluate.py \
  --model my-model \
  --provider custom \
  --custom-runner evaluate/tools/runners/my_model.py \
  --video-dir benchmark/videos
```

This is the key idea behind benchmark support for external models:

- the benchmark owns the dataset, prompt format, parsing rules, and metrics,
- the model adapter only needs to turn `(video, prompt)` into a raw text response,
- the benchmark then parses the answer and computes accuracy in a standardized way.

That is how repositories like LongVideoBench and Video-Holmes make external evaluation possible: they either provide a dataset loader / evaluation wrapper or ask users to implement a small model-specific hook. LongVideoBench exposes a dataset loader and recommends integration with a general evaluation framework, while Video-Holmes documents model-specific prepare / generate hooks inside its evaluation code. Source: [LongVideoBench README](https://github.com/longvideobench/LongVideoBench), [Video-Holmes README](https://github.com/TencentARC/Video-Holmes).

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
├── evaluate/
│   ├── evaluate.py
│   ├── results/
│   └── tools/
├── scripts/
│   └── download_data.py
├── requirements.txt
└── README.md
```

### `benchmark/`

- `benchmark/annotations/official/`: official released benchmark annotation files.
- `benchmark/annotations/splits/`: split files and construction-time partition files.
- `benchmark/annotations/legacy/`: legacy or contributor-level question files.
- `benchmark/annotations/archive/`: older assets no longer in the main release path.
- `benchmark/assets/`: benchmark plots and visual assets.
- `benchmark/videos/`: local storage directory for benchmark videos downloaded from Hugging Face.

### `evaluate/`

- `evaluate/evaluate.py`: unified evaluation entry point.
- `evaluate/results/`: main result files and archived experiments.
- `evaluate/tools/runners/`: built-in runner implementations.
- `evaluate/tools/analysis/`: analysis and formatting scripts.
- `evaluate/tools/download/`: older helper utilities related to data preparation.

### `scripts/`

- `scripts/download_data.py`: downloads benchmark videos from Hugging Face into `benchmark/videos/`.

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

## Data Access

Benchmark videos are hosted on Hugging Face:

- <https://huggingface.co/datasets/hrinnnn/PerceptionComp/tree/main>

The expected local layout after download is:

```text
benchmark/videos/<video_id>.mp4
```

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

## Related Repositories

Two good public references are:

- LongVideoBench: emphasizes dataset loading and integration with a general evaluation framework. [GitHub](https://github.com/longvideobench/LongVideoBench)
- Video-Holmes: emphasizes a polished README, download script, leaderboard presentation, and model hooks in the evaluation pipeline. [GitHub](https://github.com/TencentARC/Video-Holmes)

## Recommended Next Steps

1. Add a license and data usage statement before public release.
2. Add a small sample split for smoke testing.
3. Add a stricter public leaderboard after standardizing evaluation coverage and settings.
4. Optionally expose a dataset loader package, similar in spirit to LongVideoBench.

## Citation

If you use PerceptionComp, please cite the corresponding paper once the public version is finalized.

```bibtex
@misc{perceptioncomp2026,
  title={PerceptionComp: A Video Benchmark for Complex Perception-Centric Reasoning},
  year={2026}
}
```
