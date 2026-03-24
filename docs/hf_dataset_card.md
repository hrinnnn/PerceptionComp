---
pretty_name: PerceptionComp
license: other
task_categories:
  - video-question-answering
  - multiple-choice
language:
  - en
tags:
  - video
  - benchmark
  - multimodal
  - reasoning
  - video-understanding
  - evaluation
size_categories:
  - 1K<n<10K
---

# PerceptionComp

PerceptionComp is a benchmark for complex perception-centric video reasoning. It focuses on questions that cannot be solved from a single frame, a short clip, or a shallow caption. Models must revisit visually complex videos, gather evidence across temporally separated segments, and combine multiple perceptual cues before answering.

## Dataset Details

### Dataset Description

PerceptionComp contains 1,114 manually annotated five-choice questions associated with 273 videos. The benchmark covers seven categories: outdoor tour, shopping, sport, variety show, home tour, game, and movie.

This Hugging Face dataset repository hosts the benchmark videos. The official annotation file, evaluation code, and model integration examples are maintained in the GitHub repository:

- GitHub repository: https://github.com/hrinnnn/PerceptionComp

- **Curated by:** PerceptionComp authors
- **Language(s) (NLP):** English
- **License:** Please replace `other` in the metadata above with the final data license before public release if a more specific license applies.

### Dataset Sources

- **Repository:** https://github.com/hrinnnn/PerceptionComp
- **Paper:** Add the public paper link here when available.

## Uses

### Direct Use

PerceptionComp is intended for:

- benchmarking video-language models on complex perception-centric reasoning
- evaluating long-horizon and multi-evidence video understanding
- comparing proprietary and open-source multimodal models under a unified protocol

Users are expected to download the videos from this Hugging Face dataset and run evaluation with the official GitHub repository.

### Out-of-Scope Use

PerceptionComp is not intended for:

- unrestricted commercial redistribution of hosted videos when original source terms do not allow it
- surveillance, identity inference, or sensitive attribute prediction
- modifying the benchmark protocol and reporting those results as directly comparable official scores

## Dataset Structure

### Data Instances

Each benchmark question is associated with:

- one `video_id`
- one multiple-choice question
- five answer options
- one correct answer
- one semantic category
- one difficulty label

The official annotation file is maintained in the GitHub repository:

- `benchmark/annotations/1-1114.json`

Core fields in each annotation item:

- `key`: question identifier
- `video_id`: video filename stem without `.mp4`
- `question`: question text
- `answer_choice_0` to `answer_choice_4`: five answer options
- `answer_id`: zero-based index of the correct option
- `answer`: text form of the correct answer
- `category`: semantic category
- `difficulty`: difficulty label

### Data Files

The Hugging Face dataset stores the benchmark videos. The official evaluation code prepares them into the following local layout:

```text
benchmark/videos/<video_id>.mp4
```

Use the official download script from the GitHub repository:

```bash
git clone https://github.com/hrinnnn/PerceptionComp.git
cd PerceptionComp
pip install -r requirements.txt
python scripts/download_data.py --repo-id hrinnnn/PerceptionComp
```

### Data Splits

The current public release uses one official evaluation set:

- `1-1114.json`: 1,114 multiple-choice questions over 273 videos

## Dataset Creation

### Curation Rationale

PerceptionComp was created to evaluate a failure mode that is not well covered by simpler video benchmarks: questions that require models to combine multiple perceptual constraints over time instead of relying on a single salient frame or a short summary.

### Source Data

The benchmark uses real-world videos paired with manually written multiple-choice questions.

#### Data Collection and Processing

Videos were collected and organized for benchmark evaluation. Annotation authors then wrote perception-centric multiple-choice questions for the selected videos. Each question was designed to require visual evidence from the video rather than simple prior knowledge or caption-level shortcuts.

The release process includes:

- associating each question with a `video_id`
- formatting each sample as a five-choice multiple-choice item
- assigning semantic categories
- assigning difficulty labels
- consolidating the release into one official annotation file

#### Who are the source data producers?

The underlying videos may originate from third-party public sources. The benchmark annotations were created by the PerceptionComp authors and collaborators.

### Annotations

#### Annotation Process

PerceptionComp contains 1,114 manually annotated five-choice questions. Questions were written to test perception-centric reasoning over videos rather than single-frame recognition alone.

#### Who are the annotators?

The annotations were created by the PerceptionComp project team.

#### Personal and Sensitive Information

The videos may contain people, faces, voices, public scenes, or other naturally occurring visual content. The dataset is intended for research evaluation, not for identity inference or sensitive attribute prediction.

## Bias, Risks, and Limitations

PerceptionComp has several limitations:

- it is a multiple-choice benchmark, so performance can be affected by answer-option design
- category frequencies are not perfectly balanced
- benchmark scores do not fully measure safety, fairness, or robustness in deployment settings
- the hosted videos may inherit biases from their original sources
- downstream use may be constrained by the rights of original content owners

### Recommendations

Users should:

- report results with the official evaluation code
- avoid changing prompts, parsing rules, or metrics when claiming benchmark numbers
- verify that their usage complies with the terms of the original video sources
- avoid using the dataset for surveillance, identity recognition, or sensitive attribute inference

## Citation

If you use PerceptionComp, please cite the project paper when it is publicly available.

```bibtex
@misc{perceptioncomp2026,
  title={PerceptionComp},
  author={PerceptionComp Authors},
  year={2026},
  howpublished={Hugging Face dataset and GitHub repository}
}
```

## More Information

Official evaluation code and documentation:

- GitHub: https://github.com/hrinnnn/PerceptionComp

Example evaluation workflow:

```bash
git clone https://github.com/hrinnnn/PerceptionComp.git
cd PerceptionComp
pip install -r requirements.txt
python scripts/download_data.py --repo-id hrinnnn/PerceptionComp
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

## Dataset Card Authors

PerceptionComp authors

## Dataset Card Contact

Add the project contact email here before publishing.
