#!/usr/bin/env python3
"""Build an optional local metadata index. Markdown remains authoritative.

No model calls, session collection, material copying or source-file writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PRUNED = {'资料', 'Anki', '总管归档', '.git', '__pycache__'}
ROOT_FILES = {'学习主页.md', '规划导航.md', '课程地图.md', '交接.md', '当前模块.md', '续学位置.md'}
EVIDENCE_KINDS = {'module_handoff', 'practice_attempt'}


def validate_workspace(raw: Path) -> Path:
    raw = raw.expanduser().absolute()
    if any(p.is_symlink() for p in [raw, *raw.parents]):
        raise ValueError('Workspace path must not use symlinks.')
    root = raw.resolve()
    marker = root / 'workspace.json'
    if marker.is_symlink():
        raise ValueError('Workspace marker must not be a symlink.')
    data = json.loads(marker.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or data.get('status') != 'initialized':
        raise ValueError('Select a workspace created by the initializer.')
    return root


def metadata(value: str) -> dict:
    # Only a closed leading block counts; body examples never become metadata.
    match = re.match(r'\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)', value, re.S)
    if not match:
        return {}
    result = {}
    for key in ['kind', 'subject', 'module', 'occurred_at', 'result']:
        field = re.search(r'^' + key + r':\s*([^\r\n]+)$', match[1], re.M)
        if field:
            result[key] = field[1].strip().strip('"\'')
    return result


def collect(root: Path) -> list[dict]:
    courses = root / '科目'
    if courses.is_symlink():
        raise ValueError('Course root must not be a symlink.')
    records = []
    for directory, dirs, files in os.walk(courses, followlinks=False):
        here = Path(directory)
        dirs[:] = sorted(d for d in dirs if d not in PRUNED and not d.startswith('.')
                         and not (here / d).is_symlink())
        relative = here.relative_to(courses)
        in_records = any(part in {'模块', '学习记录', '练习'} for part in relative.parts)
        for name in sorted(files):
            path = here / name
            if path.is_symlink() or path.suffix != '.md' or name == 'README.md':
                continue
            if not in_records and name not in ROOT_FILES:
                continue
            raw = path.read_bytes()
            info = metadata(raw.decode('utf-8'))
            records.append({
                'relative_path': path.relative_to(root).as_posix(),
                'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw),
                'evidence_kind': info.get('kind') if info.get('kind') in EVIDENCE_KINDS else None,
                'subject': info.get('subject'), 'module': info.get('module'),
                'occurred_at': info.get('occurred_at'), 'declared_result': info.get('result'),
            })
    return records


def build(raw_root: Path, apply: bool = False) -> dict:
    root = validate_workspace(raw_root)
    records = collect(root)  # Finish all source reads before changing the cache.
    summary = {'files': len(records),
               'evidence_entries': sum(bool(r['evidence_kind']) for r in records),
               'applied': apply,
               'note': 'Metadata entries are pointers; inspect Markdown before judging learning.'}
    if not apply:
        return summary
    folder = root / '数据层'
    database = folder / 'catalog.sqlite3'
    if folder.is_symlink() or database.is_symlink():
        raise ValueError('Index target must not be a symlink.')
    folder.mkdir(mode=0o700, exist_ok=True)
    lock = folder / '.index.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        temp_fd, filename = tempfile.mkstemp(prefix='.catalog-', suffix='.sqlite3', dir=folder)
        os.close(temp_fd)
        temporary = Path(filename)
        with sqlite3.connect(temporary) as db:
            db.execute('CREATE TABLE files (relative_path TEXT PRIMARY KEY, sha256 TEXT NOT NULL, '
                       'bytes INTEGER NOT NULL, evidence_kind TEXT, subject TEXT, module TEXT, '
                       'occurred_at TEXT, declared_result TEXT)')
            db.executemany('INSERT INTO files VALUES (:relative_path, :sha256, :bytes, :evidence_kind, '
                           ':subject, :module, :occurred_at, :declared_result)', records)
            db.execute('CREATE TABLE index_info (schema_version INTEGER, built_at TEXT, authority TEXT)')
            db.execute('INSERT INTO index_info VALUES (1, ?, ?)',
                       (datetime.now(timezone.utc).isoformat(), 'Markdown files; this cache is not learning truth.'))
        os.replace(temporary, database)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        os.close(fd)
        lock.unlink()
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply', action='store_true', help='Rebuild the optional private SQLite cache.')
    args = parser.parse_args(argv)
    try:
        print(json.dumps(build(args.workspace, args.apply), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print('Index stopped; source Markdown unchanged: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
