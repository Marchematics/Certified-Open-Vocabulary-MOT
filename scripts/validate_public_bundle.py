#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

TOKEN_RE = re.compile(r'hf_[A-Za-z0-9]{20,}')
FORBIDDEN_PARTS = {'raw_videos', 'frames', 'images', 'hf_cache', '.cache', 'weights', 'model_weights'}
FORBIDDEN_SUFFIXES = {'.mp4', '.avi', '.mov', '.mkv', '.pth', '.pt', '.safetensors', '.ckpt'}


def main() -> None:
    parser = argparse.ArgumentParser(description='Public artifact safety scan.')
    parser.add_argument('root', nargs='?', default='.')
    args = parser.parse_args()
    root = Path(args.root)
    problems: list[str] = []
    for path in root.rglob('*'):
        if '.git' in path.parts:
            continue
        if path.is_dir():
            continue
        rel = path.relative_to(root)
        if any(part in FORBIDDEN_PARTS for part in rel.parts):
            problems.append(f'forbidden path part: {rel}')
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            problems.append(f'forbidden binary/model suffix: {rel}')
        if path.stat().st_size <= 20_000_000:
            try:
                text = path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                continue
            if TOKEN_RE.search(text):
                problems.append(f'HF token-like string: {rel}')
            local_root = '/home/waas' + '/paper_experiments'
            root_home = '/root' + '/'
            if local_root in text or root_home in text:
                problems.append(f'local absolute path: {rel}')
    if problems:
        print('\n'.join(problems))
        raise SystemExit(1)
    print('public bundle safety scan passed')


if __name__ == '__main__':
    main()
