import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('bootstrap_runtime', ROOT / 'tools/init_workspace.py')
bootstrap = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bootstrap)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name).resolve() / 'workspace'
        bootstrap.initialize(self.ws, {'schema_version': 1, 'nodes': [
            {'name': '示例', 'role': 'manager'},
            {'name': '基础', 'parent': '示例', 'role': 'leaf'},
        ]}, apply=True)
        self.leaf = self.ws / '科目/示例/基础'

    def run_cli(self, *args, expected=0, cwd=None):
        result = subprocess.run([sys.executable, str(self.ws / 'learning.py'), *args],
                                cwd=cwd or self.ws, text=True, capture_output=True)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def snapshot(self):
        return {p.relative_to(self.ws).as_posix(): p.read_bytes()
                for p in self.ws.rglob('*') if p.is_file()}

    def test_scoped_context_and_structure_are_read_only(self):
        before = self.snapshot()
        self.run_cli('doctor')
        self.run_cli('brief')
        self.run_cli('overview', '示例')
        context = self.run_cli('open', '示例/基础')
        self.assertIn('题目状态的三列记录法', context)
        self.assertIn('不使用自动保存', context)
        self.assertIn('草案', self.run_cli('plan-context', '示例/基础'))
        self.assertEqual(before, self.snapshot())

    def test_new_node_preview_apply_and_no_overwrite(self):
        args = ['new', '进阶', '--parent', '示例', '--role', 'leaf']
        before = self.snapshot()
        self.run_cli(*args)
        self.assertEqual(before, self.snapshot())
        self.run_cli(*args, '--apply')
        target = self.ws / '科目/示例/进阶'
        self.assertEqual((target / 'CLAUDE.md').read_text(), '@AGENTS.md\n')
        self.run_cli('doctor')
        after = self.snapshot()
        self.run_cli(*args, '--apply', expected=1)
        self.run_cli('new', '嵌套', '--parent', '示例/基础', '--role', 'leaf', '--apply', expected=1)
        self.run_cli('new', '../escape', '--parent', '示例', '--role', 'leaf', '--apply', expected=1)
        self.assertEqual(after, self.snapshot())

    def test_metadata_is_not_inferred_from_plans_or_body_examples(self):
        (self.leaf / '练习/计划.md').write_text('# 计划\n\nkind: practice_attempt\nresult: completed\n')
        (self.leaf / '练习/不完整文件头.md').write_text('---\nkind: practice_attempt\nresult: completed\n')
        overview = self.run_cli('overview', '示例/基础')
        self.assertIn('：0 条', overview)
        (self.leaf / '学习记录/交接01.md').write_text(
            '---\nkind: module_handoff\nsubject: 示例/基础\nmodule: 模块01\n'
            'occurred_at: 2026-10-01\nresult: partial\n---\n\n'
            '虚构测试：A独立作答，B提示后完成，C未作答；下一步恢复C。\n')
        self.assertIn('：1 条', self.run_cli('overview', '示例/基础'))
        guidance = self.run_cli('guidance-context')
        self.assertIn('partial', guidance)
        self.assertNotIn('掌握率', guidance)

    def test_checkpoint_conflict_keeps_newer_position(self):
        expected = json.loads(self.run_cli('checkpoint', '--inspect', cwd=self.leaf))['expected']
        self.run_cli('checkpoint', '--expected', expected, '--text', '虚构测试：C未作答', cwd=self.leaf)
        saved = (self.leaf / '续学位置.md').read_bytes()
        self.run_cli('checkpoint', '--expected', expected, '--text', '过期窗口的位置', cwd=self.leaf, expected=1)
        self.assertEqual(saved, (self.leaf / '续学位置.md').read_bytes())
        self.assertFalse((self.leaf / '.checkpoint.lock').exists())

    def test_explicit_material_reader_does_not_edit_book_or_learning_state(self):
        material = self.leaf / '资料/虚构材料.md'
        material.write_text('<!-- PDF_PAGE: 1 -->\n# 第一页\n这是虚构材料。\n'
                            '<!-- PDF_PAGE: 2 -->\n# 第二页\n待学习。\n')
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(self.ws / 'tools/read_study_material.py'),
                                 str(material), '--pages', '1'], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('这是虚构材料', result.stdout)
        self.assertNotIn('# 第二页', result.stdout)
        self.assertIn('链接未被自动打开', result.stdout)
        self.assertEqual(before, self.snapshot())


if __name__ == '__main__':
    unittest.main()
