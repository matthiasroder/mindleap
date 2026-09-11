import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.research_assistant import main as pipeline
from scripts.research_assistant.context import build_context
from scripts.research_assistant.state import load_state, save_state

REPO = Path(__file__).resolve().parents[1]


def article(name):
    return {
        'url': f'https://example.invalid/{name}',
        'title': name,
        'source': 'Fixture',
        'content': name,
    }


class FixtureClient:
    failure = None

    def __init__(self, **kwargs):
        self.messages = self

    def create(self, *, messages, **kwargs):
        prompt = messages[0]['content']
        if 'Rate each article' in prompt:
            if self.failure == 'filter':
                raise RuntimeError('simulated API outage')
            text = '{"0": 2}' if self.failure == 'all_negative' else '{"0": 5}'
        elif 'ARTICLE TO ANALYZE:' in prompt:
            if self.failure == 'analysis':
                raise RuntimeError('simulated API outage')
            if self.failure == 'malformed_analysis':
                text = 'An answer without the required fields.'
            else:
                text = 'SUMMARY: Fixture summary\nKEY_INSIGHT: Fixture insight\nRELEVANCE: Fixture relevance\nTAGS: test'
        elif 'TODAY\'S RELEVANT ARTICLES:' in prompt:
            if self.failure == 'synthesis':
                raise RuntimeError('simulated API outage')
            text = '- Fixture theme'
        else:
            text = 'The user is interested in fixture articles.'
        return SimpleNamespace(content=[SimpleNamespace(text=text)])


class ResearchRegressions(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.root.joinpath('IDEAS.md').write_text('Fixture interests')
        model_config = REPO / 'config' / 'research.yaml'
        if model_config.exists():
            self.root.joinpath('config').mkdir()
            self.root.joinpath('config/research.yaml').write_bytes(model_config.read_bytes())
        FixtureClient.failure = None

    def run_pipeline(self, articles):
        with patch.object(pipeline, '__file__', str(self.root / 'scripts/research_assistant/main.py')), \
             patch.object(pipeline, 'fetch_all_feeds', return_value=articles), \
             patch('anthropic.Anthropic', FixtureClient):
            pipeline.main()

    def test_same_day_runs_preserve_both_articles(self):
        self.run_pipeline([article('A')])
        self.run_pipeline([article('A'), article('B')])
        digests = '\n'.join(p.read_text() for p in self.root.joinpath('feeds').glob('*.md'))
        self.assertIn('https://example.invalid/A', digests)
        self.assertIn('https://example.invalid/B', digests)
        state = load_state(self.root / 'feeds/state.json')
        self.assertEqual(set(state['processed_urls']), {'https://example.invalid/A', 'https://example.invalid/B'})

    def test_failed_filter_does_not_complete_article(self):
        FixtureClient.failure = 'filter'
        with self.assertRaises(Exception):
            self.run_pipeline([article('A')])
        state = load_state(self.root / 'feeds/state.json')
        self.assertNotIn('https://example.invalid/A', state['processed_urls'])
        FixtureClient.failure = None
        self.run_pipeline([article('A')])
        self.assertIn('https://example.invalid/A', load_state(self.root / 'feeds/state.json')['processed_urls'])

    def test_failed_analysis_does_not_complete_article(self):
        FixtureClient.failure = 'analysis'
        with self.assertRaises(Exception):
            self.run_pipeline([article('A')])
        self.assertNotIn('https://example.invalid/A', load_state(self.root / 'feeds/state.json')['processed_urls'])

    def test_malformed_analysis_does_not_complete_article(self):
        FixtureClient.failure = 'malformed_analysis'
        with self.assertRaises(Exception):
            self.run_pipeline([article('A')])
        self.assertNotIn('https://example.invalid/A', load_state(self.root / 'feeds/state.json')['processed_urls'])

    def test_failed_synthesis_does_not_complete_article(self):
        FixtureClient.failure = 'synthesis'
        with self.assertRaises(Exception):
            self.run_pipeline([article('A')])
        self.assertNotIn('https://example.invalid/A', load_state(self.root / 'feeds/state.json')['processed_urls'])

    def test_incomplete_filter_scores_do_not_complete_articles(self):
        with self.assertRaises(Exception):
            self.run_pipeline([article('A'), article('B')])
        self.assertEqual(load_state(self.root / 'feeds/state.json')['processed_urls'], [])

    def test_successful_negative_decision_is_saved(self):
        FixtureClient.failure = 'all_negative'
        self.run_pipeline([article('A')])
        self.assertEqual(load_state(self.root / 'feeds/state.json')['processed_urls'], ['https://example.invalid/A'])
        self.assertEqual(list(self.root.joinpath('feeds').glob('*.md')), [])

    def test_workflow_stages_state_with_digest(self):
        self.root.joinpath('.gitignore').write_text(REPO.joinpath('.gitignore').read_text())
        self.root.joinpath('feeds').mkdir()
        self.root.joinpath('feeds/state.json').write_text('{"processed_urls": [], "last_run": null}')
        self.root.joinpath('feeds/digest.md').write_text('Fixture digest')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', 'add', 'feeds/'], cwd=self.root, check=True)
        staged = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], cwd=self.root, text=True)
        self.assertIn('feeds/state.json', staged.splitlines())

    def test_latest_dated_drafts_included(self):
        drafts = self.root / 'drafts'
        drafts.mkdir()
        for day in range(1, 7):
            drafts.joinpath(f'2026-09-{day:02}.md').write_text(f'Draft {day}')
        with patch('scripts.research_assistant.context.summarize_with_ai', side_effect=lambda text, *args, **kwargs: text):
            context = build_context(drafts, self.root / 'IDEAS.md')
        self.assertIn('Draft 6', context)
        self.assertNotIn('Draft 1', context)

    def test_recent_processed_urls_survive_retention(self):
        urls = [f'https://example.invalid/old-{n}' for n in range(1000)]
        state_path = self.root / 'feeds/state.json'
        save_state(state_path, {'processed_urls': urls, 'last_run': None})
        latest = 'https://example.invalid/NEW'
        self.run_pipeline([{'url': latest, 'title': 'Newest', 'source': 'Fixture', 'content': 'Newest'}])
        kept = load_state(state_path)['processed_urls']
        self.assertEqual(kept[-1], latest)
        self.assertEqual(len(kept), 1000)
        self.assertEqual(kept[0], urls[1])


if __name__ == '__main__':
    unittest.main()
