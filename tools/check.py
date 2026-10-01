#!/usr/bin/env python3
"""Check the starter's required files and simple inline Markdown file links."""

import argparse
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


REQUIRED = (
    'README.md', 'AI使用说明.md', 'CONTRIBUTING.md',
    'templates/学习主页.md', 'templates/当前模块.md', 'templates/交接.md',
    'examples/markdown/README.md', 'examples/markdown/材料.md',
    'examples/markdown/开始状态.md', 'examples/markdown/当前模块.md',
    'examples/markdown/学习主页.md', 'examples/markdown/交接.md',
    'docs/来源与设计取舍.md', 'docs/验证记录.md',
)
EXCLUDED = {'.git', '.venv', '__pycache__', 'node_modules'}
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^)\n]+)\)')
INLINE_CODE = re.compile(r'(`+).*?\1')
FENCE = re.compile(r'^\s{0,3}(`{3,}|~{3,})(.*)$')


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def check(root):
    errors = []
    documents = 0
    links = 0
    if not root.is_dir():
        return ['检查目录不存在或不是目录。'], documents, links
    for name in REQUIRED:
        p = root / name
        if not p.is_file():
            errors.append(f'{name}: 缺少必需文件')
        elif not inside(p.resolve(), root):
            errors.append(f'{name}: 必需文件指向检查目录之外')

    def walk_error(error):
        errors.append(f'目录无法读取：{error.filename}')

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for name in sorted(files):
            p = Path(directory) / name
            if p.suffix != '.md':
                continue
            label = p.relative_to(root).as_posix()
            if not inside(p.resolve(), root):
                errors.append(f'{label}: 文档指向检查目录之外，未读取')
                continue
            try:
                body = p.read_text(encoding='utf-8')
            except (OSError, UnicodeError):
                errors.append(f'{label}: 无法作为 UTF-8 文档读取')
                continue
            documents += 1
            fence = None
            for number, line in enumerate(body.splitlines(), 1):
                marker = FENCE.match(line)
                if marker:
                    token, suffix = marker.groups()
                    if fence is None:
                        fence = token
                    elif token[0] == fence[0] and len(token) >= len(fence) and not suffix.strip():
                        fence = None
                    continue
                if fence is not None:
                    continue
                line = INLINE_CODE.sub('', line)
                for match in LINK.finditer(line):
                    target = match.group(1).strip()
                    if target.startswith('<') and target.endswith('>'):
                        target = target[1:-1]
                    if target.startswith('#'):
                        continue
                    if target.startswith('/') or re.match(r'^[A-Za-z]:[\\/]', target):
                        errors.append(f'{label}:{number}: 本地链接使用绝对路径')
                        continue
                    url = urlsplit(target)
                    if url.scheme:
                        if url.scheme == 'file':
                            errors.append(f'{label}:{number}: 本地链接使用 file URI')
                        continue
                    links += 1
                    path = unquote(url.path)
                    if not path:
                        continue
                    resolved = (p.parent / path).resolve()
                    if not inside(resolved, root):
                        errors.append(f'{label}:{number}: 本地链接越出检查目录')
                    elif not resolved.exists():
                        errors.append(f'{label}:{number}: 本地链接目标不存在：{path}')
    return errors, documents, links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', type=Path,
                        default=Path(__file__).resolve().parent.parent,
                        help='候选项目根目录；默认检查工具所在项目')
    args = parser.parse_args()
    errors, documents, links = check(args.root.resolve())
    for error in errors:
        print(f'ERROR {error}')
    print(f'检查 {documents} 份 Markdown、{links} 个本地链接；错误 {len(errors)} 个。')
    print('范围：必需文件与简单内联文件链接；不验证锚点、外部网址、学习效果或 AI 接续。')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
