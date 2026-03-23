#!/usr/bin/env python3
import argparse
import importlib.util
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = ROOT / "benchmark" / "annotations" / "official" / "1-1114.json"
DEFAULT_VIDEO_DIR = ROOT / "benchmark" / "videos"
DEFAULT_OUTPUT_DIR = ROOT / "evaluate" / "results"
RUNNERS_DIR = ROOT / "evaluate" / "tools" / "runners"


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def infer_provider(model_name: str) -> str:
    lower = model_name.lower()
    if lower.startswith("gemini"):
        return "gemini"
    return "api"


def resolve_api_key(provider: str, explicit_api_key: str | None) -> str:
    if explicit_api_key:
        return explicit_api_key

    env_candidates = {
        "gemini": ["GEMINI_API_KEY", "GOOGLE_API_KEY", "API_KEY"],
        "api": ["ARK_API_KEY", "OPENAI_API_KEY", "API_KEY"],
    }
    for env_name in env_candidates[provider]:
        value = os.getenv(env_name)
        if value:
            return value

    expected = ", ".join(env_candidates[provider])
    raise ValueError(
        f"No API key found for provider '{provider}'. "
        f"Pass --api-key or set one of: {expected}."
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified evaluation entry point for PerceptionComp."
    )
    parser.add_argument("--model", required=True, help="Model name to evaluate.")
    parser.add_argument(
        "--provider",
        choices=["api", "gemini", "custom", "auto"],
        default="auto",
        help="Model backend. Defaults to auto-inference from model name.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="API key. If omitted, the script falls back to provider-specific env vars.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Base URL for OpenAI-compatible APIs. Ignored for Gemini.",
    )
    parser.add_argument(
        "--video-dir",
        default=str(DEFAULT_VIDEO_DIR),
        help="Directory containing local benchmark videos.",
    )
    parser.add_argument(
        "--annotations",
        default=str(DEFAULT_JSON),
        help="Path to the annotation JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where result files will be written.",
    )
    parser.add_argument(
        "--proxy",
        default=None,
        help="Optional proxy URL for API requests.",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=64,
        help="Number of frames to sample for OpenAI-compatible models.",
    )
    parser.add_argument(
        "--force-thinking",
        action="store_true",
        help="Gemini-only flag to retry when <think> tags are missing.",
    )
    parser.add_argument(
        "--custom-runner",
        default=None,
        help=(
            "Path to a custom runner Python file. "
            "Used when --provider custom."
        ),
    )
    parser.add_argument(
        "--custom-config",
        default=None,
        help=(
            "Optional path to a JSON/YAML/text config consumed by a custom runner. "
            "The file path is passed through as-is."
        ),
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    provider = infer_provider(args.model) if args.provider == "auto" else args.provider
    api_key = None if provider == "custom" else resolve_api_key(provider, args.api_key)

    annotations = Path(args.annotations).resolve()
    video_dir = Path(args.video_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not annotations.exists():
        raise FileNotFoundError(f"Annotation file not found: {annotations}")
    if not video_dir.exists():
        raise FileNotFoundError(
            f"Video directory not found: {video_dir}. "
            "Download the videos first, then point --video-dir to the local folder."
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    if provider == "custom":
        if not args.custom_runner:
            raise ValueError(
                "--provider custom requires --custom-runner to point to a Python file."
            )

        custom_runner_path = Path(args.custom_runner).resolve()
        if not custom_runner_path.exists():
            raise FileNotFoundError(f"Custom runner not found: {custom_runner_path}")

        runner = _load_module(custom_runner_path, "custom_runner")

        if hasattr(runner, "evaluate_with_args"):
            runner.evaluate_with_args(args)
            return

        if hasattr(runner, "evaluate"):
            runner.evaluate(
                str(video_dir),
                str(annotations),
                str(output_dir),
                args.model,
                api_key=args.api_key,
                base_url=args.base_url,
                proxy=args.proxy,
                frames=args.frames,
                custom_config=args.custom_config,
            )
            return

        raise AttributeError(
            "Custom runner must implement either `evaluate_with_args(args)` "
            "or `evaluate(video_path, json_file_path, output_path, model_name, ...)`."
        )

    if provider == "gemini":
        runner = _load_module(RUNNERS_DIR / "gemini_evaluate.py", "gemini_runner")
        runner.evaluate(
            str(video_dir),
            str(annotations),
            str(output_dir),
            args.model,
            api_key,
            args.proxy,
            force_thinking=args.force_thinking,
        )
        return

    runner = _load_module(RUNNERS_DIR / "api_evaluate.py", "api_runner")
    runner.evaluate(
        str(video_dir),
        str(annotations),
        str(output_dir),
        args.model,
        api_key,
        args.base_url,
        args.proxy,
        args.frames,
    )


if __name__ == "__main__":
    main()
