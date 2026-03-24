#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}


def build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description='Download PerceptionComp videos from Hugging Face into benchmark/videos.'
    )
    parser.add_argument(
        '--repo-id',
        default='hrinnnn/PerceptionComp',
        help='Hugging Face dataset repo id.',
    )
    parser.add_argument(
        '--repo-type',
        default='dataset',
        choices=['dataset', 'model', 'space'],
        help='Hugging Face repo type.',
    )
    parser.add_argument(
        '--hf-token',
        default=None,
        help='Optional Hugging Face token. Falls back to HF_TOKEN or HUGGINGFACE_HUB_TOKEN.',
    )
    parser.add_argument(
        '--dest',
        default=str(repo_root / 'benchmark' / 'videos'),
        help='Local destination directory for downloaded videos.',
    )
    parser.add_argument(
        '--annotation-file',
        default=str(repo_root / 'benchmark' / 'annotations' / '1-1114.json'),
        help='Annotation file used to validate that all required videos were downloaded.',
    )
    parser.add_argument(
        '--include-pattern',
        action='append',
        default=None,
        help='Additional allow pattern for snapshot_download. Can be passed multiple times.',
    )
    parser.add_argument(
        '--cache-dir',
        default=None,
        help='Optional Hugging Face cache directory.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only show what would be downloaded and copied.',
    )
    return parser


def copy_video_files(snapshot_dir: Path, dest_dir: Path, dry_run: bool) -> tuple[int, int]:
    copied = 0
    skipped = 0
    dest_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(snapshot_dir.rglob('*')):
        if not src.is_file():
            continue
        if src.suffix.lower() not in DEFAULT_VIDEO_EXTENSIONS:
            continue

        dst = dest_dir / src.name
        if dst.exists():
            if dst.stat().st_size == src.stat().st_size:
                skipped += 1
                continue
            raise RuntimeError(
                f'Conflicting duplicate filename with different size: {src.name}'
            )

        if dry_run:
            print(f'Would copy: {src} -> {dst}')
        else:
            shutil.copy2(src, dst)
            print(f'Copied: {src.name}')
        copied += 1

    return copied, skipped


def validate_download(dest_dir: Path, annotation_file: Path) -> None:
    if not annotation_file.exists():
        print(f'Validation skipped: annotation file not found at {annotation_file}')
        return

    with annotation_file.open('r', encoding='utf-8') as f:
        annotations = json.load(f)

    expected = {item['video_id'] for item in annotations if item.get('video_id')}
    available = {
        path.stem for path in dest_dir.iterdir()
        if path.is_file() and path.suffix.lower() in DEFAULT_VIDEO_EXTENSIONS
    }
    missing = sorted(expected - available)

    if missing:
        preview = ', '.join(missing[:10])
        raise RuntimeError(
            'Downloaded videos do not fully match the annotation file. '
            f'Missing {len(missing)} video(s), including: {preview}'
        )

    print(
        'Validation passed: '
        f'{len(expected)} annotated video ids are available in {dest_dir}.'
    )


def main():
    args = build_parser().parse_args()
    token = args.hf_token or os.getenv('HF_TOKEN') or os.getenv('HUGGINGFACE_HUB_TOKEN')
    dest_dir = Path(args.dest).resolve()

    allow_patterns = ['*.mp4', '*.avi', '*.mov', '*.mkv', '*.webm', '*.m4v']
    if args.include_pattern:
        allow_patterns.extend(args.include_pattern)

    with tempfile.TemporaryDirectory(prefix='perceptioncomp_hf_') as tmpdir:
        snapshot_dir = Path(tmpdir) / 'snapshot'
        print(f'Downloading {args.repo_id} ...')
        snapshot_download(
            repo_id=args.repo_id,
            repo_type=args.repo_type,
            local_dir=str(snapshot_dir),
            allow_patterns=allow_patterns,
            token=token,
            cache_dir=args.cache_dir,
        )

        copied, skipped = copy_video_files(snapshot_dir, dest_dir, args.dry_run)

    print('\nDone.')
    print(f'Destination: {dest_dir}')
    print(f'Copied: {copied}')
    print(f'Skipped existing: {skipped}')
    if not args.dry_run:
        validate_download(dest_dir, Path(args.annotation_file).resolve())


if __name__ == '__main__':
    main()
