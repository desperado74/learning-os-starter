"""Exercise the CLI on real copied projects, including deliberate failures."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parent.parent
CHECKER = PROJECT / 'tools' / 'check.py'


class CheckerCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='learning-starter-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = self.base / 'starter'
        shutil.copytree(PROJECT, self.project,
                        ignore=shutil.ignore_patterns('__pycache__', '.git'))

    def run_check(self, default=False):
        cmd = [sys.executable, str(CHECKER if default else self.project / 'tools/check.py')]
        if not default:
            cmd.append(str(self.project))
        return subprocess.run(cmd, cwd=self.base, capture_output=True, text=True)

    def add_link(self, text):
        p = self.project / 'README.md'
        p.write_text(p.read_text(encoding='utf-8') + '\n' + text + '\n', encoding='utf-8')

    def test_valid_project_from_other_working_directory(self):
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_default_root_uses_script_location(self):
        result = self.run_check(default=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_template_fails(self):
        (self.project / 'templates/交接.md').unlink()
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('templates/交接.md: 缺少必需文件', result.stdout)

    def test_broken_link_reports_source(self):
        self.add_link('[missing](不存在.md)')
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('README.md:', result.stdout)
        self.assertIn('本地链接目标不存在：不存在.md', result.stdout)

    def test_existing_outside_file_is_rejected(self):
        (self.base / 'outside.md').write_text('outside', encoding='utf-8')
        self.add_link('[outside](../outside.md)')
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('本地链接越出检查目录', result.stdout)

    def test_symlink_to_outside_is_rejected_without_reading_it(self):
        outside = self.base / 'outside.md'
        outside.write_text('private marker [bad](unreadable.md)', encoding='utf-8')
        (self.project / 'outside.md').symlink_to(outside)
        result = self.run_check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('未读取', result.stdout)
        self.assertNotIn('unreadable.md', result.stdout)

    def test_code_examples_are_not_navigation_links(self):
        self.add_link('~~~~markdown\n[example](不存在.md)\n~~~~\n`[example](不存在.md)`')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_encoded_unicode_link(self):
        self.add_link('[template](templates/%E4%BA%A4%E6%8E%A5.md)')
        result = self.run_check()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
