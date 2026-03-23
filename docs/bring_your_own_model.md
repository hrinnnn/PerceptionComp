# Bring Your Own Model

This document explains how to evaluate your own model on PerceptionComp without changing the benchmark protocol.

## What You Should and Should Not Change

Keep these benchmark-side components fixed:

- annotation file
- prompt format
- answer parsing rule
- metric computation
- output schema

Only customize the model-side inference logic:

- how the video is loaded
- how frames are prepared
- how the prompt is sent to the model
- how the raw text response is returned

This is the standard design used by public benchmark repositories: the benchmark owns evaluation logic, while the user only writes a small adapter for model inference.

## Three Integration Paths

### 1. OpenAI-Compatible API

If your model is already deployed behind an OpenAI-compatible endpoint, use:

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider api \
  --api-key YOUR_API_KEY \
  --base-url YOUR_BASE_URL \
  --video-dir benchmark/videos
```

### 2. Gemini

If your model is part of the Gemini family, use:

```bash
python evaluate/evaluate.py \
  --model YOUR_GEMINI_MODEL_NAME \
  --provider gemini \
  --api-key YOUR_GEMINI_API_KEY \
  --video-dir benchmark/videos
```

### 3. Custom Runner

If your model is local, private, or served through a different SDK, use a custom runner.

## Custom Runner Workflow

### Step 1. Copy the Template

```bash
cp evaluate/tools/runners/custom_template.py evaluate/tools/runners/my_model.py
```

### Step 2. Implement `run_your_model(...)`

Inside `my_model.py`, replace the placeholder function:

```python
def run_your_model(video_path: str, prompt: str, model_name: str, custom_config=None):
    ...
```

The function should:

- accept a local video path
- accept a fully formatted prompt string
- run your model
- return a raw string response

Recommended output formats:

```text
Answer: A
```

or

```text
<think>
reasoning here
</think>
<answer>
A
</answer>
```

## Minimal Example

```python
def run_your_model(video_path: str, prompt: str, model_name: str, custom_config=None):
    # Replace this with your own code.
    # For example:
    # 1. load video or sample frames
    # 2. call your model
    # 3. return the raw text response
    return "Answer: A"
```

## Run the Custom Evaluation

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider custom \
  --custom-runner evaluate/tools/runners/my_model.py \
  --video-dir benchmark/videos
```

If your runner uses an extra configuration file:

```bash
python evaluate/evaluate.py \
  --model YOUR_MODEL_NAME \
  --provider custom \
  --custom-runner evaluate/tools/runners/my_model.py \
  --custom-config path/to/your_config.json \
  --video-dir benchmark/videos
```

## Output Files

Results are written to:

```text
evaluate/results/Results-<model>.json
evaluate/results/Results-<model>.csv
```

The JSON file stores per-question predictions and raw responses. The CSV file stores aggregate metrics.

## Practical Recommendation

If your model can be exposed through an OpenAI-compatible API, that is usually the cleanest path. If not, keep your custom runner as thin as possible and avoid duplicating benchmark-side logic inside it.
