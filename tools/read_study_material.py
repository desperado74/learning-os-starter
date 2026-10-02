#!/usr/bin/env python3
"""Read one page-aligned book locally; no network, writes or progress inference."""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

PAGE = re.compile(r'^\s*<!--\s*PDF_PAGE:\s*(\d+)\s*-->\s*$', re.M)
CANDIDATE = re.compile(r'^#{1,6}\s+(page-(\d+)-candidate-\d+\.png)\s*$', re.M)


def norm(text: str) -> str:
    return unicodedata.normalize('NFKC', text)


def compact(text: str) -> str:
    return re.sub(r'\s+', '', norm(text))


def select_source(path: Path) -> Path:
    path = path.expanduser().resolve()
    if path.is_dir():
        preferred = sorted(path.glob('*_机器阅读版.md'))
        candidates = preferred or sorted(path.glob('*OCR底稿.md'))
        if len(candidates) != 1:
            raise ValueError('目录内没有唯一主文字版；请明确指定已有Markdown文件，不猜书籍/版本。')
        return candidates[0]
    if not path.is_file() or path.suffix.lower() != '.md':
        raise ValueError('请指定一个书籍目录或页对齐Markdown文件；PDF先通过资料索引定位文字版。')
    return path


class Book:
    def __init__(self, source: Path):
        self.source = select_source(source)
        self.root = self.source.parent
        self.text = self.source.read_text(encoding='utf-8')
        matches = list(PAGE.finditer(self.text))
        numbers = [int(m[1]) for m in matches]
        if not numbers or numbers != list(range(1, len(numbers) + 1)):
            raise ValueError('PDF_PAGE标记缺失、重复或不连续；不能自动推断页号，请核对原资料。')
        self.pages = {}
        for i, match in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.text)
            self.pages[int(match[1])] = (match.start(), end)

    def page_number(self, offset: int) -> int | None:
        return next((p for p, (a, b) in self.pages.items() if a <= offset < b), None)

    def page_text(self, number: int) -> str:
        if number not in self.pages:
            raise ValueError(f'PDF第{number}页不存在；本文件共{len(self.pages)}页。')
        a, b = self.pages[number]
        return self.text[a:b].rstrip()

    def locators(self, number: int) -> list[str]:
        result = []
        for folder in ('page_images', 'raster_pages', 'pages'):
            for suffix in ('png', 'jpg', 'jpeg'):
                path = self.root / folder / f'page-{number:03d}.{suffix}'
                if path.exists():
                    result.append(str(path))
        for link in re.findall(r'!\[[^\]]*\]\(([^)]+)\)', self.page_text(number)):
            path = self.root / link.strip('<>')
            result.append(str(path.resolve()) + ('' if path.exists() else ' [链接缺失]'))
        for path in sorted(self.root.glob('*_含目录书签.pdf')):
            result.append(f'{path} [PDF第{number}页]')
        return list(dict.fromkeys(result))

    def repairs(self, wanted: set[int]) -> list[dict]:
        """Expose records by page, never promote model confidence to truth."""
        results = []
        for path in sorted(self.root.glob('repair_ranges/**/formula_repairs_batch_*.md')):
            text = path.read_text(encoding='utf-8')
            marks = list(CANDIDATE.finditer(text))
            for i, mark in enumerate(marks):
                page = int(mark[2])
                if page not in wanted:
                    continue
                end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
                body = text[mark.end():end].strip()
                page_text = self.page_text(page)
                embedded_marks = list(CANDIDATE.finditer(page_text))
                embedded = []
                for j, item in enumerate(embedded_marks):
                    if item[1] == mark[1]:
                        stop = embedded_marks[j + 1].start() if j + 1 < len(embedded_marks) else len(page_text)
                        embedded.append(page_text[item.end():stop])
                present = bool(body and any(compact(body) in compact(part) for part in embedded))
                state = '主版同页已含此内容' if present else ('同一区域内容不同，需核图' if embedded else '主版同页未检出此内容，供核对')
                if len(embedded) > 1:
                    state = '主版同页同候选号有多条记录，须核对版本/原图；' + state
                results.append(dict(page=page, key=mark[1], source=str(path), line=text.count('\n', 0, mark.start()) + 1,
                                    state=state, body='' if present else body))
        for path in sorted(self.root.glob('repair_ranges/**/*.normalized.jsonl')):
            for line, raw in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
                if not raw.strip():
                    continue
                try:
                    row = json.loads(raw)
                    page = int(row.get('page', row.get('pdf_page', 0)))
                except (ValueError, TypeError) as exc:
                    raise ValueError(f'复核记录无法解析：{path}:{line}；未忽略该记录。') from exc
                if page not in wanted:
                    continue
                status = str(row.get('review_status', '未标明复核状态'))
                body = '\n'.join(str(row[k]) for k in ('formula', 'reviewed_text') if row.get(k))
                results.append(dict(page=page, key=f'candidate-{row.get("candidate", "?")}', source=str(path), line=line,
                                    state=f'外置复核记录：{status}；未自动合并或认定正确', body=body,
                                    image=row.get('crop', ''), reviewer=row.get('review_source', '未标明')))
        return results

    def section(self, section_id: str) -> dict:
        """Wangdao's numbered exercise sections only, excluding TOC and answers."""
        lines = self.text.splitlines(keepends=True)
        starts, offset = [], 0
        pattern = re.compile(r'^\s*(?:#{1,6}\s*)?' + re.escape(norm(section_id)) + r'\s+本节(?:习题|试题)精选\s*$')
        for line in lines:
            if pattern.fullmatch(norm(line).strip()):
                starts.append(offset)
            offset += len(line)
        if len(starts) != 1:
            raise ValueError('未定位到唯一的本节习题/试题精选正文；请用--find定位再按--pages读，不猜题组。')
        start = starts[0]
        parts = norm(section_id).split('.')
        expected_answer = '.'.join(parts[:-1] + [str(int(parts[-1]) + 1)])
        offset = start
        end = None
        for line in self.text[start:].splitlines(keepends=True):
            if offset > start and re.match(r'^\s*(?:#{1,6}\s*)?\d+(?:\.\d+){1,3}\s+答案与解析\s*$', norm(line).strip()):
                if not re.fullmatch(r'(?:#{1,6}\s*)?' + re.escape(expected_answer) + r'\s+答案与解析', norm(line).strip()):
                    raise ValueError('答案区编号不是当前王道题组的相邻编号；请按原页核对边界。')
                end = offset
                break
            # A new exercise section before its answer is not a safe boundary.
            if offset > start and re.match(r'^\s*(?:#{1,6}\s*)?\d+(?:\.\d+){1,3}\s+本节(?:习题|试题)精选\s*$', norm(line).strip()):
                raise ValueError('题组结束位置有歧义；请按物理页核对。')
            offset += len(line)
        if end is None:
            raise ValueError('未找到明确的答案区边界；请按物理页读取，不自动输出后续章节。')
        body = self.text[start:end].rstrip()
        first, last = self.page_number(start), self.page_number(end - 1)
        groups = []
        current = None
        choice = None
        choices = []
        in_repair = False
        for line in body.splitlines():
            if PAGE.fullmatch(line):
                in_repair = False
            if '本页模型校正区域' in line:
                in_repair = True
            if in_repair:
                continue
            clean = norm(line).strip()
            match = re.fullmatch(r'(?:[一二三四五六七八九十]+、)?(单项选择题|多项选择题|综合应用题|填空题|解答题)', clean)
            if match:
                current = {'type': match[1], 'ids': []}
                groups.append(current)
                choice = None
            elif current:
                match = re.match(r'^(\d{2})\.', clean)
                if match:
                    current['ids'].append(int(match[1]))
                    choice = None
                    if '选择题' in current['type']:
                        choice = {'type': current['type'], 'id': int(match[1]), 'labels': []}
                        choices.append(choice)
                if choice:
                    choice['labels'].extend(re.findall(r'(?:^|\s)([A-D])[.、]', clean))
        issues = [f'{c["type"]}{c["id"]:02d}：选项标签读序为{c["labels"]}，不是完整A/B/C/D；须核原页，不能猜补或仅排序。'
                  for c in choices if c['labels'] != list('ABCD')]
        return dict(body=body, first=first, last=last, groups=groups,
                    issues=issues,
                    lines=(self.text.count('\n', 0, start) + 1, self.text.count('\n', 0, end)))


def parse_pages(value: str) -> list[int]:
    numbers = []
    for part in value.split(','):
        match = re.fullmatch(r'(\d+)(?:-(\d+))?', part.strip())
        if not match:
            raise ValueError('页码格式应为15或14-15或14,17；使用PDF物理页，不是书页。')
        first, last = int(match[1]), int(match[2] or match[1])
        if first < 1 or last < first or last - first > 20:
            raise ValueError('请给有效的小范围页码，每次最多21页。')
        numbers.extend(range(first, last + 1))
    if len(set(numbers)) > 21:
        raise ValueError('每次最多21页，请分段读取。')
    return sorted(set(numbers))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='一个书籍目录或页对齐Markdown')
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument('--inspect', action='store_true')
    actions.add_argument('--find', help='支持半角/全角等价查找，不按固定行号读取')
    actions.add_argument('--pages', help='PDF物理页，如14-15')
    actions.add_argument('--section', help='王道式本节试题精选编号，如1.1.3；输出完整题组及题型顺序')
    parser.add_argument('--max-chars', type=int, default=30000, help='超限报出位置，不静默截断正文/修订')
    args = parser.parse_args(argv)
    try:
        book = Book(args.source)
        out = [f'来源：{book.source}', '只读材料；不判断已做题、不推进学习进度。PDF_PAGE指物理页。']
        if 'OCR底稿' in book.source.name:
            out.append('当前入口是OCR底稿：须一并核对外置复核记录；目录存在主机器阅读版时优先改用主版。')
        if args.inspect:
            records = book.repairs(set(book.pages))
            embedded = sum(r['state'] == '主版同页已含此内容' for r in records)
            out += [f'物理页标记：1—{len(book.pages)}，连续且唯一。',
                    f'复核记录：{len(records)}；主版同区域含同文：{embedded}；其他记录：{len(records)-embedded}。',
                    '这验证可定位性，不验证OCR或模型修订在语义上正确。']
        elif args.find:
            query = norm(args.find)
            if not query.strip():
                raise ValueError('搜索词不能为空。')
            hits, offset = [], 0
            for line_no, line in enumerate(book.text.splitlines(keepends=True), 1):
                if query in norm(line):
                    hits.append(f'PDF页{book.page_number(offset)}，行{line_no}：{line.strip()}')
                offset += len(line)
            out += hits[:12]
            out += [f'共{len(hits)}处；最多展示12处，目录匹配不等于题目正文。']
        else:
            group = book.section(args.section) if args.section else None
            numbers = list(range(group['first'], group['last'] + 1)) if group else parse_pages(args.pages)
            if group:
                out.append(f'题组{args.section}；PDF页{group["first"]}—{group["last"]}；原文行{group["lines"]}。')
                for g in group['groups']:
                    ids = g['ids']
                    out.append(f'顺序子组：{g["type"]}，检出题号{ids}（OCR候选，须与原题清单核对）。')
                out += ['选项排版疑点：' + item for item in group['issues']]
                out.append('选项标签检查只是风险提示；未报疑点不代表内容、公式或归属已核实。')
                out.append('本题组所有子组处理后才进入下一小节；题号清单中的未完状态优先，不能只凭上一条回复跳组。')
                out.append('呈题前逐题检查选项标签及归属；多栏OCR可能把上一题D选项放入下一题，OCR_TEXT_SUFFICIENT不保证选项无错位。疑点须看原页。')
                out.append(group['body'])
            else:
                out += [book.page_text(n) for n in numbers]
            records = book.repairs(set(numbers))
            out.append('\n同页复核记录（区域级，不代表整页已验收）：')
            for r in records:
                out.append(f'PDF页{r["page"]} {r["key"]}｜{r["state"]}｜{r["source"]}:{r["line"]}')
                if r.get('image'):
                    out.append(f'候选原图：{r["image"]}')
                if r['body'] and not group:
                    out.append(r['body'])
            if group:
                out.append('题组输出不附带答案区后的同页修订正文；需核疑点时用--pages读完整页和对应修订，再只展示原题。')
            out.append('\n原页/候选图定位（链接未被自动打开；必要时使用图像查看工具）：')
            for n in numbers:
                locations = book.locators(n)
                out += [f'PDF页{n}：{path}' for path in locations]
                if not locations:
                    out.append(f'PDF页{n}：未找到现成图像或带书签PDF，请按资料索引到原PDF渲染该页。')
        result = '\n\n'.join(out)
        if len(result) > args.max_chars:
            raise ValueError(f'完整结果为{len(result)}字符，超过输出预算{args.max_chars}；请缩小页范围或显式提高--max-chars。未输出截断正文。')
        print(result)
        return 0
    except (OSError, ValueError) as exc:
        print(f'材料读取未完成：{exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
