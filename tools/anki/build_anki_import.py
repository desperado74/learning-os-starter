#!/usr/bin/env python3
"""Build an Anki-importable TSV from common question/card source files."""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


FRONT_KEYS = (
    "front",
    "question",
    "prompt",
    "cue",
    "term",
    "sentence",
    "item",
    "q",
    "text",
)
BACK_KEYS = (
    "back",
    "answer",
    "response",
    "translation",
    "definition",
    "expected_answer",
    "a",
)
EXTRA_KEYS = (
    "extra",
    "explanation",
    "rationale",
    "note",
    "notes",
    "comment",
    "comments",
    "context",
)
SOURCE_KEYS = (
    "source",
    "source_file",
    "origin",
    "scenario",
    "lesson",
    "section",
    "id",
    "uid",
)
TAGS_KEYS = ("tags", "tag")
LIST_CONTAINER_KEYS = ("cards", "notes", "questions", "items", "entries")


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value).strip()
    if isinstance(value, list):
        return "\n".join(as_text(item) for item in value if as_text(item)).strip()
    return json.dumps(value, ensure_ascii=False, sort_keys=True).strip()


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")


def normalize_front(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


from formatting import render_text as html_text


def find_value(item: dict[str, Any], candidates: Iterable[str], override: str | None = None) -> str:
    normalized = {normalize_key(key): value for key, value in item.items()}
    if override:
        value = normalized.get(normalize_key(override))
        if value is not None:
            return as_text(value)
    for candidate in candidates:
        value = normalized.get(normalize_key(candidate))
        if value is not None:
            return as_text(value)
    return ""


def split_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        raw_parts = [as_text(part) for part in value]
    else:
        raw_parts = re.split(r"[,;\s]+", as_text(value))
    tags: list[str] = []
    seen: set[str] = set()
    for part in raw_parts:
        tag = re.sub(r"\s+", "_", part.strip())
        tag = tag.strip(",;")
        if not tag:
            continue
        if tag not in seen:
            tags.append(tag)
            seen.add(tag)
    return tags


def merge_tags(*tag_groups: Any) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in tag_groups:
        for tag in split_tags(group):
            if tag not in seen:
                merged.append(tag)
                seen.add(tag)
    return merged


from formatting import back_html as compose_back


def object_to_card(
    item: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[str, str, list[str]]:
    front = find_value(item, FRONT_KEYS, args.front_key)
    answer = find_value(item, BACK_KEYS, args.back_key)
    extra = find_value(item, EXTRA_KEYS, args.extra_key)
    source = find_value(item, SOURCE_KEYS, args.source_key)
    tags_value = find_value(item, TAGS_KEYS, args.tags_key)

    back = compose_back(answer, extra, source if args.include_source else "")
    tags = merge_tags(tags_value)
    return front, back, tags


def load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        for key in LIST_CONTAINER_KEYS:
            value = data.get(key)
            if isinstance(value, list):
                items = value
                break
        else:
            items = [data]
    else:
        raise ValueError("JSON input must be an object, list, or object containing a card list.")
    return [coerce_mapping(item) for item in items]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(coerce_mapping(json.loads(line)))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL on line {line_no}: {exc}") from exc
    return rows


def load_delimited(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:4096]
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",\t;|").delimiter
    except csv.Error:
        pass

    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return []

    first = [normalize_key(cell) for cell in rows[0]]
    known = set(FRONT_KEYS + BACK_KEYS + EXTRA_KEYS + SOURCE_KEYS + TAGS_KEYS)
    has_header = bool(set(first) & {normalize_key(key) for key in known})

    if has_header:
        headers = rows[0]
        return [
            {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            for row in rows[1:]
        ]

    items: list[dict[str, Any]] = []
    for row in rows:
        items.append(
            {
                "front": row[0] if len(row) > 0 else "",
                "back": row[1] if len(row) > 1 else "",
                "extra": row[2] if len(row) > 2 else "",
                "tags": row[3] if len(row) > 3 else "",
            }
        )
    return items


def load_markdown_table(lines: list[str]) -> list[dict[str, Any]]:
    table_lines = [line for line in lines if line.strip().startswith("|") and line.strip().endswith("|")]
    if len(table_lines) < 3:
        return []
    header = [cell.strip() for cell in table_lines[0].strip("|").split("|")]
    separator = [cell.strip() for cell in table_lines[1].strip("|").split("|")]
    if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
        return []
    items: list[dict[str, Any]] = []
    for line in table_lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        items.append({header[i]: cells[i] if i < len(cells) else "" for i in range(len(header))})
    return items


def load_markdown(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    table_items = load_markdown_table(lines)
    if table_items:
        return table_items

    items: list[dict[str, Any]] = []
    current: dict[str, list[str]] = {}
    active_key: str | None = None
    marker_pattern = re.compile(
        r"^\s*(?:[-*]\s*)?(?:\*\*)?(q|question|front|a|answer|back|extra|explanation|source|tags)(?:\*\*)?\s*[:：]\s*(.*)$",
        re.IGNORECASE,
    )

    def flush() -> None:
        nonlocal current
        if current:
            item = {key: "\n".join(value).strip() for key, value in current.items()}
            if item.get("front") or item.get("back"):
                items.append(item)
        current = {}

    for line in lines:
        match = marker_pattern.match(line)
        if match:
            marker, value = match.groups()
            key = normalize_key(marker)
            if key in {"q", "question"}:
                key = "front"
            elif key in {"a", "answer"}:
                key = "back"
            elif key == "explanation":
                key = "extra"
            if key == "front" and current.get("front") and current.get("back"):
                flush()
            active_key = key
            current.setdefault(key, []).append(value.strip())
            continue

        if active_key and line.strip():
            current.setdefault(active_key, []).append(line.strip())

    flush()
    return items


def coerce_mapping(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if isinstance(item, list):
        return {
            "front": item[0] if len(item) > 0 else "",
            "back": item[1] if len(item) > 1 else "",
            "extra": item[2] if len(item) > 2 else "",
            "tags": item[3] if len(item) > 3 else "",
        }
    return {"front": as_text(item), "back": ""}


def load_items(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_json(path)
    if suffix in {".jsonl", ".ndjson"}:
        return load_jsonl(path)
    if suffix in {".csv", ".tsv"}:
        return load_delimited(path)
    if suffix in {".md", ".markdown", ".txt"}:
        return load_markdown(path)
    raise ValueError(f"Unsupported input type: {suffix or '(no extension)'}")


def write_tsv(
    rows: list[tuple[str, str, list[str]]],
    output: Path,
    deck: str,
    notetype: str,
    global_tags: list[str],
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        handle.write("#separator:tab\n")
        handle.write("#html:true\n")
        if notetype:
            handle.write(f"#notetype:{notetype}\n")
        if deck:
            handle.write(f"#deck:{deck}\n")
        if global_tags:
            handle.write(f"#tags:{' '.join(global_tags)}\n")
        handle.write("#columns:Front\tBack\tTags\n")
        handle.write("#tags column:3\n")
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        for front, back, tags in rows:
            writer.writerow([front, back, " ".join(tags)])


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(input_path.suffix + ".anki.tsv")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON, JSONL, CSV, TSV, Markdown, or TXT source file.")
    parser.add_argument("--output", "-o", type=Path, help="Output TSV path.")
    parser.add_argument("--deck", default="", help="Existing Anki deck header to embed. Leave empty to omit #deck.")
    parser.add_argument("--notetype", default="Basic", help="Anki note type header to embed.")
    parser.add_argument("--tags", nargs="*", default=[], help="Global tags to add through the #tags header.")
    parser.add_argument("--front-key", help="Override source key for Front.")
    parser.add_argument("--back-key", help="Override source key for Back.")
    parser.add_argument("--extra-key", help="Override source key for Explanation/extra content.")
    parser.add_argument("--source-key", help="Override source key for source/context content.")
    parser.add_argument("--tags-key", help="Override source key for row-specific tags.")
    parser.add_argument(
        "--include-source",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Append detected source/context information to the Back field.",
    )
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Do not deduplicate rows with the same normalized Front field.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2

    try:
        items = load_items(args.input)
    except Exception as exc:
        print(f"Could not read input: {exc}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, list[str]]] = []
    seen: dict[str, str] = {}
    skipped_missing = 0
    skipped_duplicate = 0

    for item in items:
        front, back, tags = object_to_card(item, args)
        if not front or not back:
            skipped_missing += 1
            continue
        key = normalize_front(front)
        if not args.allow_duplicates and key in seen:
            if seen[key] != back:
                print('Conflicting answers for the same front; output not written.', file=sys.stderr)
                return 2
            skipped_duplicate += 1
            continue
        seen[key] = back
        rows.append((html_text(front), back, tags))

    output = args.output or default_output_path(args.input)
    if output.resolve() == args.input.resolve():
        print('Output must not overwrite the source file.', file=sys.stderr)
        return 2
    write_tsv(rows, output, args.deck, args.notetype, split_tags(args.tags))

    print(f"Wrote {len(rows)} cards to {output}")
    if skipped_missing:
        print(f"Skipped {skipped_missing} rows missing front or back")
    if skipped_duplicate:
        print(f"Skipped {skipped_duplicate} duplicate rows")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
