#!/usr/bin/env python3
import argparse
import shutil
from pathlib import Path


VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v'}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            'Normalize a manually downloaded Hugging Face video folder into '
            'the benchmark/videos/<video_id>.mp4-style layout expected by PerceptionComp.'
        )
    )
    parser.add_argument(
        '--src',
        required=True,
        help='Path to the manually downloaded Hugging Face folder or snapshot directory.',
    )
    parser.add_argument(
        '--dest',
        default=str(Path(__file__).resolve().parents[1] / 'benchmark' / 'videos'),
        help='Destination directory. Defaults to benchmark/videos.',
    )
    parser.add_argument(
        '--move',
        action='store_true',
        help='Move files instead of copying them.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only show what would be normalized.',
    )
    return parser


def normalize_videos(src_dir: Path, dest_dir: Path, move: bool, dry_run: bool) -> tuple[int, int]:
    copied = 0
    skipped = 0
    action = 'Move' if move else 'Copy'
    transfer = shutil.move if move else shutil.copy2

    dest_dir.mkdir(parents=True, exist_ok=True)

    for src in sorted(src_dir.rglob('*')):
        if not src.is_file():
            continue
        if src.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        dst = dest_dir / src.name
        if dst.exists():
            if dst.stat().st_size == src.stat().st_size:
                skipped += 1
                print(f'Skip existing: {src.name}')
                continue
            raise RuntimeError(
                f'Conflicting duplicate filename with different size: {src.name}'
            )

        if dry_run:
            print(f'Would {action.lower()}: {src} -> {dst}')
        else:
            transfer(str(src), str(dst))
            print(f'{action}d: {src.name}')
        copied += 1

    return copied, skipped


def main():
    args = build_parser().parse_args()
    src_dir = Path(args.src).resolve()
    dest_dir = Path(args.dest).resolve()

    if not src_dir.exists():
        raise FileNotFoundError(f'Source directory does not exist: {src_dir}')
    if not src_dir.is_dir():
        raise NotADirectoryError(f'Source path is not a directory: {src_dir}')

    copied, skipped = normalize_videos(
        src_dir=src_dir,
        dest_dir=dest_dir,
        move=args.move,
        dry_run=args.dry_run,
    )

    print('\nDone.')
    print(f'Source: {src_dir}')
    print(f'Destination: {dest_dir}')
    print(f'Processed: {copied}')
    print(f'Skipped existing: {skipped}')


if __name__ == '__main__':
    main()
