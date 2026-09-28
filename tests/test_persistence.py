"""Prove that local publication survives concurrency and interrupted writes."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

from scripts.research_assistant import main as pipeline
from scripts.research_assistant.llm import ResearchError
from scripts.research_assistant.output import write_digest
from scripts.research_assistant.persistence import PENDING_RUN, research_lock
from scripts.research_assistant.state import load_state, record_completed, save_state, seen_urls
import test_regressions as fixtures
from test_regressions import FixtureClient, article, REPO


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        # Reuse the offline API fixture without inheriting/rerunning its tests.
        self.case = fixtures.ResearchRegressions()
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = self.case.root
        self.feeds = self.root / 'feeds'
        self.state_path = self.feeds / 'state.json'

    def test_retry_recovers_state_failure_without_model_calls_or_duplicates(self):
        self.case.run_pipeline([article('A')])
        before = self.state_path.read_bytes()
        with patch('scripts.research_assistant.persistence.save_state', side_effect=OSError('disk failure')):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.case.run_pipeline([article('A'), article('B')])
        self.assertEqual(self.state_path.read_bytes(), before)
        digest = next(self.feeds.glob('*.md'))
        published = digest.read_bytes()
        count = len(FixtureClient.calls)
        self.assertTrue((self.feeds / PENDING_RUN).exists())
        # Even --reprocess must finish the pending run without repeating it.
        self.case.run_pipeline([article('A'), article('B')], reprocess=True)
        self.assertEqual(len(FixtureClient.calls), count)
        self.assertEqual(digest.read_bytes(), published)
        self.assertEqual(published.count(b'https://example.invalid/B'), 1)
        self.assertEqual(seen_urls(load_state(self.state_path)), {article('A')['url'], article('B')['url']})
        self.assertFalse((self.feeds / PENDING_RUN).exists())

    def test_retry_recovers_digest_failure_before_advancing_history(self):
        with patch('scripts.research_assistant.persistence.write_digest', side_effect=OSError('digest disk failure')):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('A')])
        self.assertFalse(self.state_path.exists())
        self.assertEqual(list(self.feeds.glob('*.md')), [])
        calls = len(FixtureClient.calls)
        self.case.run_pipeline([article('A')])
        self.assertEqual(len(FixtureClient.calls), calls)
        self.assertEqual(len(list(self.feeds.glob('*.md'))), 1)
        self.assertEqual(seen_urls(load_state(self.state_path)), {article('A')['url']})

    def test_failed_journal_write_publishes_nothing(self):
        with patch('scripts.research_assistant.persistence._save_pending', side_effect=OSError('journal disk failure')):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('A')])
        self.assertFalse(self.state_path.exists())
        self.assertEqual(list(self.feeds.glob('*.md')), [])

    def test_interrupted_reprocess_recovery_keeps_history_bytes_unchanged(self):
        self.case.run_pipeline([article('A')])
        history = self.state_path.read_bytes()
        with patch('scripts.research_assistant.persistence.write_digest', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('B')], reprocess=True)
        calls = len(FixtureClient.calls)
        self.case.run_pipeline([article('B')], reprocess=True)
        self.assertEqual(self.state_path.read_bytes(), history)
        self.assertEqual(len(FixtureClient.calls), calls)
        self.assertEqual(next(self.feeds.glob('*.md')).read_text().count(article('B')['url']), 1)

    def test_completed_run_with_journal_left_behind_is_not_published_again(self):
        original_unlink = Path.unlink
        def interrupted_unlink(path, *args, **kwargs):
            if path.name == PENDING_RUN:
                raise OSError('interrupted journal cleanup')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', interrupted_unlink):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('A')])
        digest = next(self.feeds.glob('*.md'))
        before = digest.read_bytes()
        self.case.run_pipeline([article('A')])
        self.assertEqual(digest.read_bytes(), before)
        self.assertFalse((self.feeds / PENDING_RUN).exists())

    def test_corrupt_journal_cannot_reset_history_or_write_outside_feeds(self):
        self.case.run_pipeline([article('A')])
        state = self.state_path.read_bytes()
        journal = self.feeds / PENDING_RUN
        journal.write_text('{broken')
        with self.assertRaises(ResearchError):
            self.case.run_pipeline([article('B')])
        self.assertEqual(self.state_path.read_bytes(), state)
        journal.unlink()
        with patch('scripts.research_assistant.persistence.save_state', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('A'), article('B')])
        pending = json.loads(journal.read_text())
        pending['date'] = '../outside'
        journal.write_text(json.dumps(pending))
        with self.assertRaisesRegex(ResearchError, 'Invalid pending'):
            self.case.run_pipeline([article('B')])
        self.assertFalse((self.root / 'outside.md').exists())
        self.assertEqual(self.state_path.read_bytes(), state)

    def test_recovery_refuses_to_overwrite_unrelated_history_changes(self):
        with patch('scripts.research_assistant.persistence.save_state', side_effect=OSError('disk')):
            with self.assertRaises(OSError):
                self.case.run_pipeline([article('A')])
        changed = record_completed(load_state(self.state_path), [article('External')['url']], 'external')
        save_state(self.state_path, changed)
        before = self.state_path.read_bytes()
        with self.assertRaisesRegex(ResearchError, 'History changed'):
            self.case.run_pipeline([article('A')])
        self.assertEqual(self.state_path.read_bytes(), before)

    def test_concurrent_digest_appends_preserve_every_run(self):
        digest = self.feeds / '2026-09-29.md'
        self.feeds.mkdir()
        digest.write_text('# Original\n\n')
        start = threading.Barrier(6)
        original_read = Path.read_bytes
        def slow_read(path):
            content = original_read(path)
            time.sleep(0.025)
            return content
        def append(index):
            start.wait(timeout=5)
            write_digest(digest, [article(str(index))], '- Theme', '2026-09-29')
        with patch.object(Path, 'read_bytes', slow_read), ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(append, range(6)))
        content = digest.read_text()
        self.assertTrue(content.startswith('# Original\n\n'))
        self.assertEqual(content.count('## Run at '), 6)
        for index in range(6):
            self.assertEqual(content.count(f'https://example.invalid/{index}'), 1)

    def test_another_process_cannot_enter_and_crash_releases_lock(self):
        child = subprocess.Popen(
            [sys.executable, '-c',
             'import sys; from pathlib import Path; from scripts.research_assistant.persistence import research_lock; '
             'lock = research_lock(Path(sys.argv[1])); lock.__enter__(); print("locked", flush=True); sys.stdin.readline()',
             str(self.feeds)],
            cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            self.assertEqual(child.stdout.readline().strip(), 'locked')
            with self.assertRaisesRegex(ResearchError, 'Another research run'):
                self.case.run_pipeline([article('A')])
            self.assertEqual(FixtureClient.calls, [])
            child.kill()
            child.communicate(timeout=5)
            with research_lock(self.feeds):
                pass
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=5)

    def test_feed_failure_causes_nonzero_cli_status_without_calling_models(self):
        with patch.object(pipeline, '__file__', str(self.root / 'scripts/research_assistant/main.py')), patch.object(pipeline, 'fetch_all_feeds', side_effect=ResearchError('Feed offline')), patch.object(sys, 'argv', ['research']):
            self.assertEqual(pipeline.cli(), 1)
        self.assertEqual(FixtureClient.calls, [])
        self.assertFalse(self.state_path.exists())


if __name__ == '__main__':
    unittest.main()
