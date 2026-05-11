#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

PLACEHOLDER = '${PARC_TRACK_ROOT}'


def main() -> None:
    parser = argparse.ArgumentParser(description='Render sanitized configs with a local PARC_TRACK_ROOT path.')
    parser.add_argument('--root', required=True, help='Local experiment root to substitute for ${PARC_TRACK_ROOT}.')
    parser.add_argument('--config-dir', default='configs', help='Input config directory.')
    parser.add_argument('--out', required=True, help='Output config directory.')
    args = parser.parse_args()
    src = Path(args.config_dir)
    dst = Path(args.out)
    dst.mkdir(parents=True, exist_ok=True)
    for path in src.rglob('*'):
        rel = path.relative_to(src)
        target = dst / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            target.write_bytes(path.read_bytes())
        else:
            target.write_text(text.replace(PLACEHOLDER, args.root), encoding='utf-8')


if __name__ == '__main__':
    main()
