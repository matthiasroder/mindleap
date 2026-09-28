"""Exercise source retrieval and evidence boundaries with offline fixtures."""
from email.message import Message
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.research_assistant.analyze import analyze_articles
from scripts.research_assistant.articles import read_article, MAX_ARTICLE_CHARACTERS
from scripts.research_assistant.context import build_context
from scripts.research_assistant.feeds import fetch_feed, fetch_all_feeds, load_feed_config
from scripts.research_assistant.llm import ResearchError
from scripts.research_assistant.network import Download, download, REQUEST_TIMEOUT
from scripts.research_assistant.synthesize import synthesize_themes


ARTICLE = {
    'url': 'https://example.invalid/article', 'title': 'City libraries',
    'source': 'Fixture', 'content': 'Article URL: https://example.invalid/article Points: 30 Comments: 8',
}
TEXT = '''The city library opened a new reading room this week after a year of planning.
The room provides quiet desks, accessible seating, and a collection of local history books.
Residents helped decide which services should be available by attending a series of public meetings.
The library director said that opening hours will remain unchanged during the first month.
Staff will collect feedback from visitors before making any further adjustments to the space.
The project used an existing room rather than building an extension, reducing construction work.
Volunteers catalogued donated materials and prepared an exhibition about the neighborhood's history.
Visitors can reserve a desk in advance or use the seats available for people who walk in.'''


class ArticleTests(unittest.TestCase):
    def test_real_extractor_supplies_article_text_instead_of_feed_metadata(self):
        html = '<html><body><nav><a href="/login">Navigation login</a></nav><article><h1>City libraries</h1>'
        html += ''.join(f'<p>{paragraph}</p>' for paragraph in TEXT.splitlines()) + '</article></body></html>'
        with patch('scripts.research_assistant.articles.download', return_value=Download(html.encode(), ARTICLE['url'], 'text/html')):
            result = read_article(ARTICLE)
        self.assertEqual(result['content_status'], 'retrieved')
        self.assertIn('quiet desks', result['content'])
        self.assertNotIn('Points:', result['content'])
        self.assertNotIn('Navigation login', result['content'])
        with patch('scripts.research_assistant.analyze.complete_text', return_value='SUMMARY: Library\nKEY_INSIGHT: Community input\nRELEVANCE: Public spaces\nTAGS: cities') as model:
            analyzed = analyze_articles([result], 'Libraries')
        self.assertIn('quiet desks', model.call_args.kwargs['prompt'])
        self.assertEqual(analyzed[0]['summary'], 'Library')

    def test_failed_or_insufficient_retrieval_never_generates_article_claims(self):
        outcomes = [
            ResearchError('connection timed out'),
            Download(b'<html><p>Please log in.</p></html>', ARTICLE['url'], 'text/html'),
            Download(b'%PDF-fixture', ARTICLE['url'], 'application/pdf'),
        ]
        for outcome in outcomes:
            with self.subTest(outcome=type(outcome).__name__):
                with patch('scripts.research_assistant.articles.download') as fetch:
                    if isinstance(outcome, Exception):
                        fetch.side_effect = outcome
                    else:
                        fetch.return_value = outcome
                    result = read_article(ARTICLE)
                with patch('scripts.research_assistant.analyze.complete_text') as analysis, patch('scripts.research_assistant.synthesize.complete_text') as synthesis:
                    analyzed = analyze_articles([result], 'Libraries')
                    themes = synthesize_themes(analyzed)
                analysis.assert_not_called()
                synthesis.assert_not_called()
                self.assertIn('Link only', result['evidence'])
                self.assertIn('No themes inferred', themes)

    def test_long_articles_are_capped_and_labeled_as_excerpts(self):
        with patch('scripts.research_assistant.articles.download', return_value=Download((TEXT * 50).encode(), ARTICLE['url'], 'text/plain')):
            result = read_article(ARTICLE)
        self.assertEqual(len(result['content']), MAX_ARTICLE_CHARACTERS)
        self.assertIn('first 30,000 characters', result['evidence'])

    def test_link_only_entries_are_excluded_from_mixed_themes(self):
        read = dict(ARTICLE, content_status='retrieved', summary='Verified library report')
        unread = dict(ARTICLE, content_status='unavailable', summary='UNREAD_SENTINEL')
        with patch('scripts.research_assistant.synthesize.complete_text', return_value='- Theme') as model:
            synthesize_themes([read, unread])
        self.assertNotIn('UNREAD_SENTINEL', model.call_args.kwargs['prompt'])


class FeedTests(unittest.TestCase):
    def test_large_archive_feeds_are_bounded_before_model_processing(self):
        items = ''.join(f'<item><title>Item {index}</title><link>https://example.invalid/{index}</link></item>' for index in range(60))
        body = f'<rss version="2.0"><channel><title>Archive</title>{items}</channel></rss>'.encode()
        with patch('scripts.research_assistant.feeds.download', return_value=Download(body, 'https://example.invalid/feed', 'application/rss+xml')):
            self.assertEqual(len(fetch_feed({'name': 'Archive', 'url': 'https://example.invalid/feed'})), 50)
            self.assertEqual(len(fetch_feed({'name': 'Archive', 'url': 'https://example.invalid/feed', 'max_articles': 10})), 10)

    def test_valid_empty_feed_differs_from_failed_feed(self):
        body = b'<?xml version="1.0"?><rss version="2.0"><channel><title>Empty</title></channel></rss>'
        with patch('scripts.research_assistant.feeds.download', return_value=Download(body, 'https://example.invalid/feed', 'application/rss+xml')):
            self.assertEqual(fetch_feed({'name': 'Empty', 'url': 'https://example.invalid/feed'}), [])
        with patch('scripts.research_assistant.feeds.download', side_effect=ResearchError('timeout')):
            with self.assertRaisesRegex(ResearchError, 'Empty.*timeout'):
                fetch_feed({'name': 'Empty', 'url': 'https://example.invalid/feed'})

    def test_html_error_page_is_not_an_empty_feed(self):
        with patch('scripts.research_assistant.feeds.download', return_value=Download(b'<html><body>Access denied</body></html>', 'https://example.invalid/feed', 'text/html')):
            with self.assertRaises(ResearchError):
                fetch_feed({'name': 'Blocked', 'url': 'https://example.invalid/feed'})

    def test_failed_source_stops_batch_instead_of_silently_omitting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'feeds.yaml'
            config.write_text('feeds:\n  - name: Broken\n    url: https://example.invalid/feed\n')
            with patch('scripts.research_assistant.feeds.download', side_effect=ResearchError('timeout')):
                with self.assertRaisesRegex(ResearchError, 'Broken'):
                    fetch_all_feeds(config)

    def test_invalid_feed_config_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'feeds.yaml'
            for text in ('', 'feeds: wrong', 'feeds: [null]', 'feeds: [{name: Missing URL}]', 'feeds: [{name: Bad limit, url: https://example.invalid, max_articles: false}]'):
                config.write_text(text)
                with self.subTest(text=text), self.assertRaises(ResearchError):
                    load_feed_config(config)

    def test_html_entities_and_relative_links_are_resolved(self):
        body = b'''<rss version="2.0"><channel><title>Fixture</title><item><title>A</title><link>/article</link><description>&lt;p&gt;Salt &amp;amp; pepper&lt;/p&gt;</description></item></channel></rss>'''
        with patch('scripts.research_assistant.feeds.download', return_value=Download(body, 'https://example.invalid/feed', 'application/rss+xml')):
            result = fetch_feed({'name': 'Fixture', 'url': 'https://example.invalid/feed'})
        self.assertEqual(result[0]['url'], 'https://example.invalid/article')
        self.assertEqual(result[0]['content'], 'Salt & pepper')


class DownloadTests(unittest.TestCase):
    def setUp(self):
        dns = patch('scripts.research_assistant.network.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))])
        self.dns = dns.start()
        self.addCleanup(dns.stop)

    def test_timeout_and_response_limit_apply_before_parsing(self):
        headers = Message()
        headers['Content-Type'] = 'text/html'
        with patch('scripts.research_assistant.network.build_opener') as opener:
            open_url = opener.return_value.open
            response = open_url.return_value.__enter__.return_value
            response.headers = headers
            response.read.return_value = b'123456789'
            with patch('scripts.research_assistant.network.MAX_RESPONSE_BYTES', 8):
                with self.assertRaisesRegex(ResearchError, 'exceeds'):
                    download(ARTICLE['url'])
            response.read.assert_called_once_with(9)
            self.assertEqual(open_url.call_args.kwargs['timeout'], REQUEST_TIMEOUT)

    def test_local_files_are_not_downloadable(self):
        with patch('scripts.research_assistant.network.build_opener') as open_url:
            with self.assertRaisesRegex(ResearchError, 'HTTP'):
                download('file:///etc/passwd')
            open_url.assert_not_called()

    def test_local_network_addresses_and_redirects_are_rejected(self):
        from urllib.request import Request
        from scripts.research_assistant.network import _PublicRedirects
        self.dns.return_value = [(2, 1, 6, '', ('127.0.0.1', 80))]
        with patch('scripts.research_assistant.network.build_opener') as opener:
            with self.assertRaisesRegex(ResearchError, 'public addresses'):
                download('http://localhost/private')
            opener.assert_not_called()
        with self.assertRaisesRegex(ResearchError, 'public addresses'):
            _PublicRedirects().redirect_request(Request(ARTICLE['url']), None, 302, 'Found', {}, 'http://127.0.0.1/private')


class IdeasTests(unittest.TestCase):
    def test_only_five_newest_opted_in_ideas_enter_research_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ideas = root / 'ideas'
            ideas.mkdir()
            for day in range(1, 8):
                (ideas / f'2026-09-{day:02}-idea.md').write_text(f'---\nresearch: true\n---\nSelected-{day}')
            (ideas / '2026-09-09-retired.md').write_text('---\nresearch: false\n---\nRETIRED_SENTINEL')
            (ideas / '2026-09-10-unselected.md').write_text('UNSELECTED_SENTINEL')
            with patch('scripts.research_assistant.context.summarize_with_ai', side_effect=lambda text, **kwargs: text):
                result = build_context(root / 'drafts', root / 'IDEAS.md', ideas_dir=ideas)
            self.assertIn('Selected-7', result)
            self.assertIn('Selected-3', result)
            for excluded in ('Selected-1', 'Selected-2', 'RETIRED_SENTINEL', 'UNSELECTED_SENTINEL'):
                self.assertNotIn(excluded, result)

    def test_invalid_selection_metadata_fails_clearly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'broken.md').write_text('---\nresearch: "true"\n---\nIdea')
            with self.assertRaisesRegex(ResearchError, 'research must be true or false'):
                build_context(root / 'drafts', root / 'IDEAS.md', ideas_dir=root)


if __name__ == '__main__':
    unittest.main()
