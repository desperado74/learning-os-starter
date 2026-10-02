#!/usr/bin/env python3
"""Replay a fictional FILE workflow, not an AI or real learner evaluation."""
from __future__ import annotations
import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load('init_workspace')
index = load('build_index')
CONFIG = {'schema_version': 1, 'profile': {
    'goals': '虚构演示：理解平均数', 'habits': '虚构演示：先例子再练习'}, 'nodes': [
    {'name': '统计', 'role': 'manager'},
    {'name': '平均数', 'parent': '统计', 'role': 'leaf', 'materials': ['资料/材料.md']},
]}
MATERIAL = '''# 虚构原创材料：平均数

所有题目与答案均为项目编写的演示数据，不是作者或真实用户的学习记录。

算术平均数为总和除以数量，数量必须大于零。合并不同大小的分组时，先恢复各组总和再除以总数量。

A：求2、4、6的平均数。
B：一组2人的平均数为10，另一组1人的平均数为16，合并后平均数是多少？
C：求3、7的平均数，并说明为什么除以2。
'''
PAUSE = '''# 模块01：平均数（虚构演示）

规划依据：依照[原创材料](../资料/材料.md)学习算术平均数与合并分组；范围只有A、B、C。
终止点：三题均处理并完成反馈。下一个模块待规划，不自动启动。

| 原题 | 作答证据 | 处置决定 | 后续动作 |
| --- | --- | --- | --- |
| A | 独立正确：虚构作答“(2+4+6)/3=4” | 正常纳入，已处理 | 无需回收 |
| B | 提示后完成：先提示恢复两组总和，再虚构作答“(2×10+16)/3=12” | 正常纳入，已处理 | 独立验证方法选择 |
| C | 无本题作答证据 | 正常纳入，未处理 | 等待补做 |

暂停后先独立验证B的方法选择，再处理C。提示后完成不是独立掌握。
'''
FINISH = PAUSE.replace(
    '| C | 无本题作答证据 | 正常纳入，未处理 | 等待补做 |',
    '| C | 独立正确：虚构作答“(3+7)/2=5，数量为2” | 正常纳入，已处理 | 自然回访 |'
) + '''
## 第二次会话的虚构记录

保留B的首次提示记录。先在无提示条件下用相似分组核对：3人均值4、1人均值8，虚构作答“(3×4+8)/4=5”。这支持本次方法选择，不删除首次提示历史，也不保证长期掌握。

C已独立处理；A、B、C均完成本模块要求。到此收尾，不展示下一模块内容。
'''


def handoff(result, body):
    return ('---\nkind: module_handoff\nsubject: 统计/平均数\nmodule: 模块01\n'
            'occurred_at: 2026-10-02\nresult: ' + result + '\n---\n\n'
            '# 虚构演示交接\n\n本文件为脚本生成的演示，不是实际学习证据。\n\n'
            + body + '\n\n唯一记录：[当前模块](../模块/模块01.md)。\n')


def replay(target: Path, apply=False):
    initial = bootstrap.initialize(target, CONFIG, apply=False)
    additions = [f'科目/统计/平均数/{p}' for p in [
        '资料/材料.md', '模块/模块01.md', '学习记录/暂停.md', '学习记录/完成.md',
        '练习/第二次作答.md', 'Anki/待导入/候选.jsonl']]
    if not apply:
        return {'simulation': True, 'applied': False, 'files': initial + additions,
                'optional_cache': '数据层/catalog.sqlite3'}
    bootstrap.initialize(target, CONFIG, apply=True)
    target = target.resolve()
    leaf = target / '科目/统计/平均数'
    (leaf / '资料/材料.md').write_text(MATERIAL, encoding='utf-8')
    (leaf / '模块/模块01.md').write_text(PAUSE, encoding='utf-8')
    partial = handoff('partial', 'A独立完成；B提示后完成；C未作答。下一次先独立核对B，再处理C。')
    (leaf / '学习记录/暂停.md').write_text(partial, encoding='utf-8')
    pause_saved = (leaf / '模块/模块01.md').read_text(encoding='utf-8')
    # This simulates a NEW reader from disk, with no model invoked.
    resume_files = [(leaf / p).read_text(encoding='utf-8') for p in ['模块/模块01.md', '学习记录/暂停.md']]
    assert all('提示后完成' in value and 'C' in value for value in resume_files)
    (leaf / '模块/模块01.md').write_text(FINISH, encoding='utf-8')
    attempt = ('---\nkind: practice_attempt\nsubject: 统计/平均数\nmodule: 模块01\n'
               'occurred_at: 2026-10-02\nresult: completed\n---\n\n'
               '# 虚构演示作答\n\n脚本生成，不是实际用户作答。\n\n'
               'B类题无提示作答：(3×4+8)/4=5。C无提示作答：(3+7)/2=5，数量为2。\n')
    (leaf / '练习/第二次作答.md').write_text(attempt, encoding='utf-8')
    completed = handoff('completed', '指定三题已处理；B首次提示后完成的历史保留。下一模块待规划；没有长期掌握结论。')
    (leaf / '学习记录/完成.md').write_text(completed, encoding='utf-8')
    completed += ('\n## 接续提示词\n\n```text\n请在 ' + str(leaf) +
                  ' 接续。先读本节点AGENTS.md与规则索引，再读学习主页、学习记录/完成.md和模块/模块01.md。'
                  '核对实际文件与历史提示；本模块已收尾，下一模块待规划。先按长期主线与材料讨论范围，不直接出题。\n```\n')
    (leaf / '学习记录/完成.md').write_text(completed, encoding='utf-8')
    page = (leaf / '学习主页.md').read_text(encoding='utf-8')
    page = page.replace('尚未开始；初始化不证明学习发生。',
                        '虚构演示模块已收尾；见[完成交接](学习记录/完成.md)与[唯一模块记录](模块/模块01.md)。')
    (leaf / '学习主页.md').write_text(page, encoding='utf-8')
    candidate = leaf / 'Anki/待导入/候选.jsonl'
    candidate.parent.mkdir(parents=True)
    candidate.write_text(json.dumps({'front': '合并不同人数的平均数时，先求什么？',
        'back': '各组总和与总人数，再相除。', 'source': '虚构模块01', 'tags': ['demo']}, ensure_ascii=False) + '\n', encoding='utf-8')
    # No Anki configuration or import: a saved candidate is not an enabled integration.
    cache = index.build(target, apply=True)
    check = subprocess.run([sys.executable, str(target / 'learning.py'), 'doctor'],
                           cwd=target, text=True, capture_output=True)
    if check.returncode:
        raise ValueError(check.stdout + check.stderr)
    assert (leaf / '学习记录/暂停.md').read_text(encoding='utf-8') == partial
    assert '无本题作答证据' in pause_saved
    return {'simulation': True, 'applied': True, 'resume_verified_from_files': True,
            'final_handoff': 'completed', 'index': cache,
            'anki_imported': False, 'model_tested': False, 'source_system_accessed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(replay(args.workspace, args.apply), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print('Fictional replay stopped: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
