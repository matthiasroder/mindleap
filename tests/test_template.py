"""Check the template as a fresh user would receive it; no credentials needed."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import yaml

REPO = Path(__file__).resolve().parents[1]


class TemplateTests(unittest.TestCase):
    def test_every_documented_skill_has_portable_packaging(self):
        readme = (REPO / 'README.md').read_text()
        advertised = set(re.findall(r'^\| `/([a-z-]+)`', readme, re.MULTILINE))
        self.assertTrue(advertised)
        for name in advertised:
            with self.subTest(skill=name):
                command = REPO / '.claude/commands' / f'{name}.md'
                if command.exists():
                    continue
                folder = REPO / '.claude/skills' / name
                # Inspect the actual spelling, including on case-insensitive macOS.
                self.assertIn('SKILL.md', [entry.name for entry in folder.iterdir()])
                text = (folder / 'SKILL.md').read_text()
                self.assertTrue(text.startswith('---\n'))
                metadata = yaml.safe_load(text.split('---', 2)[1])
                self.assertEqual(metadata['name'], name)
                self.assertTrue(metadata['description'].strip())

    def test_shared_settings_do_not_grant_all_shell_commands(self):
        config = json.loads((REPO / '.claude/settings.json').read_text())
        allowed = config.get('permissions', {}).get('allow', [])
        self.assertFalse({'Bash', 'Bash(*)', 'Bash(:*)'} & set(allowed))

    def test_local_settings_and_recovery_files_are_not_added_to_vault(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copyfile(REPO / '.gitignore', root / '.gitignore')
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            private = [
                '.claude/settings.local.json', 'feeds/.research.lock',
                'feeds/.2026-09-29.md.lock', 'feeds/.pending-run.json',
                'feeds/..pending-run.json.random.tmp',
            ]
            for name in private + ['feeds/state.json', 'feeds/2026-09-29.md']:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=root, text=True).splitlines()
            self.assertEqual(set(staged), {'.gitignore', 'feeds/state.json', 'feeds/2026-09-29.md'})


@unittest.skipIf(os.name == 'nt', 'The vault sync helper requires Bash')
class SyncTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.vault = self.root / 'vault with spaces'
        (self.vault / 'scripts').mkdir(parents=True)
        self.script = self.vault / 'scripts/sync.sh'
        shutil.copyfile(REPO / 'scripts/sync.sh', self.script)
        (self.vault / 'README.md').write_text('Vault marker\nAn instructional @Claude mention\n')
        (self.vault / 'USER.md').write_text('- [x] @Claude Already done\n')
        (self.vault / 'IDEAS.md').write_text('- [ ] @Claude Real task\n')
        self.caller = self.root / 'unrelated'
        self.caller.mkdir()
        binary = self.root / 'bin'
        binary.mkdir()
        stub = binary / 'git'
        stub.write_text('#!/bin/sh\nprintf "GIT_CWD=%s ARGS=%s\\n" "$PWD" "$*"\nif [ "$1" = pull ]; then exit "${TEST_PULL_STATUS:-0}"; fi\n')
        stub.chmod(0o755)
        self.env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'])

    def test_script_always_uses_its_own_vault(self):
        for setting in (None, '', str(self.root / 'missing'), str(self.caller)):
            with self.subTest(environment=setting):
                env = self.env.copy()
                if setting is None:
                    env.pop('CLAUDE_PROJECT_DIR', None)
                else:
                    env['CLAUDE_PROJECT_DIR'] = setting
                run = subprocess.run(['bash', str(self.script)], cwd=self.caller, env=env, capture_output=True, text=True, check=True)
                self.assertIn(f'GIT_CWD={self.vault} ARGS=pull --ff-only', run.stdout)
                self.assertIn('Vault marker', run.stdout)
                tasks = run.stdout.split('=== @CLAUDE TODOS ===')[1]
                self.assertIn('Real task', tasks)
                self.assertNotIn('Already done', tasks)
                self.assertNotIn('instructional', tasks)

    def test_failed_pull_stops_before_processing_tasks(self):
        run = subprocess.run(['bash', str(self.script)], cwd=self.caller, env=dict(self.env, TEST_PULL_STATUS='1'), capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn('Vault sync failed', run.stderr)
        self.assertNotIn('Real task', run.stdout)


if __name__ == '__main__':
    unittest.main()
