import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('cycle_demo', ROOT / 'examples/full-cycle/demo.py')
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class FullCycleTests(unittest.TestCase):
    def test_fictional_cycle_preserves_partial_history_and_does_not_import_anki(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp).resolve() / 'new'
            preview = demo.replay(target)
            self.assertFalse(target.exists())
            self.assertFalse(preview['applied'])
            result = demo.replay(target, True)
            self.assertTrue(result['resume_verified_from_files'])
            self.assertFalse(result['model_tested'])
            leaf = target / '科目/统计/平均数'
            self.assertIn('result: partial', (leaf / '学习记录/暂停.md').read_text())
            self.assertIn('result: completed', (leaf / '学习记录/完成.md').read_text())
            self.assertIn('首次提示记录', (leaf / '模块/模块01.md').read_text())
            self.assertFalse((leaf / 'Anki/已导入').exists())
            self.assertFalse((leaf / 'Anki/配置.json').exists())
            self.assertTrue((target / '数据层/catalog.sqlite3').is_file())


if __name__ == '__main__':
    unittest.main()
