# PerceptionComp

PerceptionComp is a benchmark for complex perception-centric video reasoning. It is designed for questions that cannot be solved from a single frame, a single moment, or a short caption: models must revisit visually complex videos, gather evidence from temporally separated segments, and combine multiple perceptual constraints before answering.

This repository is the benchmark-and-evaluation workspace for PerceptionComp: A Video Benchmark for Complex Perception-Centric Reasoning.

## Overview

PerceptionComp focuses on a harder form of video understanding than standard short-video QA. The benchmark is built around:

- perception-heavy questions grounded in real video content,
- temporally distributed evidence,
- compositional constraints across multiple sub-conditions, and
- five-choice evaluation for stable automatic scoring.

From the current paper draft:

- the benchmark contains 1,114 manually annotated multiple-choice questions,
- each question is designed to require repeated perception rather than single-pass viewing,
- single-view human performance drops sharply, while unrestricted rewatching remains much easier for experts,
- frontier multimodal models still lag well behind careful human reasoning.

## Quick Start

Clone the repository, install dependencies, download benchmark videos from Hugging Face, and run evaluation.

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

If the Hugging Face dataset requires authentication, you can additionally pass:

```bash
python scripts/download_data.py \
  --repo-id hrinnnn/PerceptionComp \
  --hf-token YOUR_HF_TOKEN
```

For Gemini models:

```bash
python evaluate/evaluate.py \
  --model gemini-2.5-flash \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

## Current Repository Snapshot

The current repository snapshot contains:

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

This folder contains the benchmark itself.

- `benchmark/annotations/official/`
  Official released benchmark annotation files.
- `benchmark/annotations/splits/`
  Split files and working partition files used during dataset construction and evaluation.
- `benchmark/annotations/legacy/`
  Legacy or contributor-level question files preserved for reference.
- `benchmark/annotations/archive/`
  Archived question assets that are no longer part of the main release path.
- `benchmark/assets/`
  Benchmark plots and dataset-related visual assets.
- `benchmark/videos/`
  Local storage directory for benchmark videos downloaded from Hugging Face.

### `evaluate/`

This folder contains evaluation code and archived results.

- `evaluate/evaluate.py`
  Unified evaluation entry point.
- `evaluate/results/`
  Main result files plus archived seasonal or round-based evaluation dumps.
- `evaluate/tools/runners/`
  Lightweight model-facing evaluation entry scripts.
- `evaluate/tools/analysis/`
  Analysis, formatting, cleanup, and statistics scripts.
- `evaluate/tools/download/`
  Video download and related data-preparation utilities.

### `scripts/`

- `scripts/download_data.py`
  Downloads benchmark videos from Hugging Face into `benchmark/videos/`.

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

See [schema.md](/Users/zhaozhixuan/Desktop/tsinghua_learning/大二暑/暑研/PerceptionComp/benchmark/annotations/schema.md) for a compact schema reference.

## Data Access

Benchmark videos are hosted on Hugging Face at:

- <https://huggingface.co/datasets/hrinnnn/PerceptionComp/tree/main>

The expected local layout after download is:

```text
benchmark/videos/<video_id>.mp4
```

## Evaluation

There is now a unified evaluation entry point at `evaluate/evaluate.py`.

Example usage with an OpenAI-compatible API:

```bash
python evaluate/evaluate.py \
  --model gpt-5.2 \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

Example usage with Gemini:

```bash
python evaluate/evaluate.py \
  --model gemini-2.5-flash \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

If `--provider auto` is used, models starting with `gemini` are routed to the Gemini runner and all others are routed to the OpenAI-compatible API runner.

## Evaluation Assets

This repository already includes a substantial amount of evaluation history. The current structure separates:

- main result files in `evaluate/results/`,
- archived seasonal or round-based experiment folders in `evaluate/results/archive/`, and
- analysis or runner scripts in `evaluate/tools/`.

These result files are useful as working records and internal baselines. They should be treated as archived experiment artifacts rather than a finalized public leaderboard.

## Recommended Next Steps

The repository is now organized around `benchmark/` and `evaluate/`, but the next cleanup steps are still important:

1. Add a license and data usage statement before public release.
2. Add a small sample split for smoke testing.
3. Gradually merge duplicated legacy evaluation scripts into the unified entry point.
4. Optionally publish a lightweight leaderboard table in the README.

## Citation

If you use PerceptionComp, please cite the corresponding paper once the public version is finalized.

```bibtex
@misc{perceptioncomp2026,
  title={PerceptionComp: A Video Benchmark for Complex Perception-Centric Reasoning},
  year={2026}
}
```
