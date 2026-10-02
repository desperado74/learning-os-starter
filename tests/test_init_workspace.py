import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('initializer',
    Path(__file__).resolve().parents[1] / 'tools/init_workspace.py')
init = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(init)


def configuration():
    return {'schema_version': 1, 'profile': {'interests': '虚构测试 / Fictional test'},
            'nodes': [{'name': '科学', 'role': 'manager'},
                      {'name': '入门', 'parent': '科学', 'role': 'leaf',
                       'materials': ['/fictional/missing/book.pdf']}]}


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.parent = Path(self.temp.name).resolve()
        self.target = self.parent / 'private'

    def test_dry_run_does_not_create_any_files(self):
        before = list(self.parent.iterdir())
        planned = init.initialize(self.target, configuration())
        self.assertIn('科目/科学/入门/AGENTS.md', planned)
        self.assertEqual(before, list(self.parent.iterdir()))

    def test_complete_creation_preserves_unknowns_and_materials_as_references(self):
        planned = init.initialize(self.target, configuration(), apply=True)
        actual = sorted(p.relative_to(self.target).as_posix()
                        for p in self.target.rglob('*') if p.is_file())
        self.assertEqual(planned, actual)
        data = json.loads((self.target / 'workspace.json').read_text())
        self.assertEqual(data['nodes'], {'科学': 'manager', '科学/入门': 'leaf'})
        self.assertIn('Unknown', (self.target / '个人学习画像.md').read_text())
        leaf = self.target / '科目/科学/入门'
        self.assertEqual((leaf / 'CLAUDE.md').read_text(), '@AGENTS.md\n')
        self.assertIn('../../../AGENTS.md', (leaf / 'AGENTS.md').read_text())
        self.assertIn('/fictional/missing/book.pdf', (leaf / '学习主页.md').read_text())
        self.assertEqual(list((leaf / '资料').iterdir()), [leaf / '资料/README.md'])
        self.assertFalse((leaf / '当前模块.md').exists())
        self.assertFalse((self.target / '.git').exists())

    def test_existing_workspace_is_never_changed(self):
        self.target.mkdir()
        evidence = self.target / '真实作答.md'
        evidence.write_bytes(b'original evidence\x00')
        with self.assertRaises(ValueError):
            init.initialize(self.target, configuration(), apply=True)
        self.assertEqual(evidence.read_bytes(), b'original evidence\x00')
        self.assertEqual(list(self.target.iterdir()), [evidence])

    def test_invalid_hierarchy_leaves_no_partial_files(self):
        config = configuration()
        config['nodes'][0]['role'] = 'leaf'
        with self.assertRaises(ValueError):
            init.initialize(self.target, config, apply=True)
        self.assertFalse(self.target.exists())

    def test_traversal_duplicate_and_unknown_fields_rejected_before_write(self):
        for bad in ['../escape', 'a/b', 'CON', 'a\nb']:
            config = configuration()
            config['nodes'][0]['name'] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                init.initialize(self.target, config, apply=True)
            self.assertFalse(self.target.exists())
        config = configuration()
        config['profile']['api_key'] = 'fictional'
        with self.assertRaises(ValueError):
            init.initialize(self.target, config, apply=True)
        config = configuration()
        config['nodes'].append({'name': '科学', 'role': 'manager'})
        with self.assertRaises(ValueError):
            init.initialize(self.target, config, apply=True)
        self.assertFalse(self.target.exists())

    def test_repository_and_git_ancestor_refused(self):
        with self.assertRaises(ValueError):
            init.validate_target(init.REPOSITORY / 'private')
        checkout = self.parent / 'checkout'
        checkout.mkdir()
        (checkout / '.git').write_text('gitdir: fictional')
        with self.assertRaises(ValueError):
            init.validate_target(checkout / 'private')
        self.assertFalse((checkout / 'private').exists())

    def test_symlink_target_or_parent_cannot_redirect_writes(self):
        real = self.parent / 'real'
        real.mkdir()
        link = self.parent / 'link'
        try:
            link.symlink_to(real, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable on this platform')
        with self.assertRaises(ValueError):
            init.initialize(link / 'new', configuration(), apply=True)
        self.assertEqual(list(real.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
