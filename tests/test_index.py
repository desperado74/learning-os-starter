import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bootstrap = load('init_workspace')
index = load('build_index')


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ws = Path(self.temp.name).resolve() / 'private'
        bootstrap.initialize(self.ws, {'schema_version': 1, 'nodes': [
            {'name': '测试', 'role': 'leaf'}]}, True)
        self.leaf = self.ws / '科目/测试'

    def source_snapshot(self):
        return {p.relative_to(self.ws).as_posix(): p.read_bytes()
                for p in self.ws.rglob('*') if p.is_file() and '数据层' not in p.parts}

    def test_preview_and_rebuild_leave_sources_unchanged(self):
        before = self.source_snapshot()
        summary = index.build(self.ws)
        self.assertFalse(summary['applied'])
        self.assertFalse((self.ws / '数据层').exists())
        index.build(self.ws, True)
        self.assertEqual(before, self.source_snapshot())
        with sqlite3.connect(self.ws / '数据层/catalog.sqlite3') as db:
            columns = [row[1] for row in db.execute('PRAGMA table_info(files)')]
            self.assertNotIn('content', columns)
            self.assertNotIn('mastery', columns)
            self.assertFalse(any('个人学习画像' in r[0] for r in db.execute('SELECT relative_path FROM files')))

    def test_body_example_is_not_evidence_and_deleted_entry_disappears(self):
        plan = self.leaf / '模块/计划.md'
        plan.write_text('# 草案\n\nkind: practice_attempt\nresult: completed\n')
        attempt = self.leaf / '练习/作答.md'
        attempt.write_text('---\nkind: practice_attempt\nsubject: 测试\nmodule: 01\n'
                           'result: partial\n---\n\n虚构作答。\n')
        self.assertEqual(index.build(self.ws, True)['evidence_entries'], 1)
        attempt.unlink()
        self.assertEqual(index.build(self.ws, True)['evidence_entries'], 0)
        with sqlite3.connect(self.ws / '数据层/catalog.sqlite3') as db:
            self.assertFalse(any(r[0].endswith('作答.md') for r in db.execute('SELECT relative_path FROM files')))

    def test_materials_and_symlinks_are_excluded(self):
        book = self.leaf / '资料/私有教材.md'
        book.write_text('DO NOT INDEX BOOK CONTENT')
        outside = Path(self.temp.name).resolve() / 'outside.md'
        outside.write_text('DO NOT READ OUTSIDE')
        try:
            (self.leaf / '练习/external.md').symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable')
        paths = [r['relative_path'] for r in index.collect(self.ws)]
        self.assertFalse(any('私有教材' in p or 'external' in p for p in paths))

    def test_invalid_utf8_cannot_replace_previous_index(self):
        index.build(self.ws, True)
        db = self.ws / '数据层/catalog.sqlite3'
        before = db.read_bytes()
        (self.leaf / '练习/损坏.md').write_bytes(b'\xff')
        with self.assertRaises(ValueError):
            index.build(self.ws, True)
        self.assertEqual(before, db.read_bytes())


if __name__ == '__main__':
    unittest.main()
