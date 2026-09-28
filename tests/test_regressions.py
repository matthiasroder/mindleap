import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts.research_assistant import main as pipeline
from scripts.research_assistant.context import build_context
from scripts.research_assistant.llm import ModelConfigError, ResearchError, load_models
from scripts.research_assistant.output import write_digest
from scripts.research_assistant.state import (
    load_state,
    record_completed,
    save_state,
    seen_urls,
)

REPO = Path(__file__).resolve().parents[1]


def article(name):
    return {
        "url": f"https://example.invalid/{name}",
        "title": name,
        "source": "Fixture",
        "content": name,
        "published": "2026-09-11",
    }


class FixtureClient:
    scenario = None
    calls = []
    filter_calls = 0

    def __init__(self, **kwargs):
        self.messages = self

    def create(self, *, messages, model, max_tokens):
        prompt = messages[0]["content"]
        self.__class__.calls.append((model, prompt))
        stop_reason = "end_turn"

        if "Rate each article" in prompt:
            self.__class__.filter_calls += 1
            if self.scenario == "filter_failure":
                raise RuntimeError("simulated API outage")
            if self.scenario == "late_filter_failure" and self.filter_calls == 2:
                raise RuntimeError("simulated late API outage")
            count = len(re.findall(r'^\d+\. "', prompt, re.MULTILINE))
            score = 2 if self.scenario == "all_negative" else 5
            pairs = [f'"{index}": {score}' for index in range(count)]
            if self.scenario == "incomplete_filter" and pairs:
                pairs.pop()
            text = "{" + ", ".join(pairs) + "}"
        elif "ARTICLE TO ANALYZE:" in prompt:
            if self.scenario == "analysis_failure":
                raise RuntimeError("simulated API outage")
            if self.scenario == "malformed_analysis":
                text = "An answer without the required fields."
            else:
                text = (
                    "SUMMARY: Fixture summary\n"
                    "KEY_INSIGHT: Fixture insight\n"
                    "RELEVANCE: Fixture relevance\n"
                    "TAGS: test"
                )
        elif "TODAY'S RELEVANT ARTICLES:" in prompt:
            if self.scenario == "synthesis_failure":
                raise RuntimeError("simulated API outage")
            text = "- Fixture theme"
        else:
            text = "The user is interested in fixture articles."
            if self.scenario == "truncated_context":
                stop_reason = "max_tokens"
            elif self.scenario == "empty_context":
                text = "   "

        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=text)],
            stop_reason=stop_reason,
        )


class ResearchRegressions(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.root.joinpath("IDEAS.md").write_text("Fixture interests")
        self.root.joinpath("config").mkdir()
        self.root.joinpath("config/research.yaml").write_bytes(
            REPO.joinpath("config/research.yaml").read_bytes()
        )
        FixtureClient.scenario = None
        FixtureClient.calls = []
        FixtureClient.filter_calls = 0

    def run_pipeline(self, articles, *, reprocess=False):
        with (
            patch.object(
                pipeline,
                "__file__",
                str(self.root / "scripts/research_assistant/main.py"),
            ),
            patch.object(pipeline, "fetch_all_feeds", return_value=articles),
            patch.object(pipeline, "read_articles", side_effect=lambda items: [
                {**item, "content_status": "retrieved", "evidence": "Retrieved fixture article text."}
                for item in items
            ]),
            patch("anthropic.Anthropic", FixtureClient),
        ):
            pipeline.main(reprocess=reprocess)

    def test_config_propagates_four_independent_models(self):
        self.root.joinpath("config/research.yaml").write_text(
            "models:\n"
            "  context: context-model-1\n"
            "  filter: filter-model-2\n"
            "  analysis: analysis-model-3\n"
            "  synthesis: synthesis-model-4\n"
        )
        self.run_pipeline([article("A")])
        self.assertEqual(
            [call[0] for call in FixtureClient.calls],
            [
                "context-model-1",
                "filter-model-2",
                "analysis-model-3",
                "synthesis-model-4",
            ],
        )

    def test_partial_config_uses_defaults_and_rejects_bad_keys(self):
        path = self.root / "config/research.yaml"
        path.write_text("models:\n  analysis: custom.analysis:v2\n")
        models = load_models(path)
        self.assertEqual(models.analysis, "custom.analysis:v2")
        self.assertEqual(models.context, "claude-haiku-4-5-20251001")

        path.write_text("models:\n  analyser: model-name\n")
        with self.assertRaisesRegex(ModelConfigError, "analyser"):
            load_models(path)
        path.write_text("models:\n  filter: 'bad model name'\n")
        with self.assertRaisesRegex(ModelConfigError, "models.filter"):
            load_models(path)

    def test_selected_model_failure_has_no_fallback(self):
        self.root.joinpath("config/research.yaml").write_text(
            "models:\n  filter: user-selected-model\n"
        )
        FixtureClient.scenario = "filter_failure"
        with self.assertRaisesRegex(ResearchError, "user-selected-model.*no fallback"):
            self.run_pipeline([article("A")])
        filter_models = [
            model for model, prompt in FixtureClient.calls if "Rate each article" in prompt
        ]
        self.assertEqual(filter_models, ["user-selected-model"])
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())

    def test_truncated_response_does_not_complete_article(self):
        FixtureClient.scenario = "truncated_context"
        with self.assertRaisesRegex(ResearchError, "truncated"):
            self.run_pipeline([article("A")])
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())

    def test_empty_response_does_not_complete_article(self):
        FixtureClient.scenario = "empty_context"
        with self.assertRaisesRegex(ResearchError, "contained no text"):
            self.run_pipeline([article("A")])
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())

    def test_late_filter_failure_publishes_and_completes_nothing(self):
        FixtureClient.scenario = "late_filter_failure"
        articles = [article(str(index)) for index in range(21)]
        with self.assertRaisesRegex(ResearchError, "late API outage"):
            self.run_pipeline(articles)
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())
        self.assertEqual(list(self.root.joinpath("feeds").glob("*.md")), [])

    def test_malformed_filter_and_analysis_do_not_complete_articles(self):
        FixtureClient.scenario = "incomplete_filter"
        with self.assertRaisesRegex(ResearchError, "incomplete scores"):
            self.run_pipeline([article("A"), article("B")])

        FixtureClient.scenario = "malformed_analysis"
        with self.assertRaisesRegex(ResearchError, "required fields"):
            self.run_pipeline([article("A")])
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())

    def test_synthesis_failure_does_not_publish_or_complete(self):
        FixtureClient.scenario = "synthesis_failure"
        with self.assertRaisesRegex(ResearchError, "synthesis model"):
            self.run_pipeline([article("A")])
        self.assertEqual(seen_urls(load_state(self.root / "feeds/state.json")), set())
        self.assertEqual(list(self.root.joinpath("feeds").glob("*.md")), [])

    def test_successful_all_negative_filter_advances_state(self):
        FixtureClient.scenario = "all_negative"
        self.run_pipeline([article("A"), article("A")])
        state = load_state(self.root / "feeds/state.json")
        self.assertEqual(state["processed_urls"], ["https://example.invalid/A"])
        self.assertEqual(list(self.root.joinpath("feeds").glob("*.md")), [])

    def test_mixed_linkless_feed_only_processes_valid_article(self):
        linkless = article("Linkless")
        linkless["url"] = ""
        self.run_pipeline([linkless, article("Valid")])

        prompts = [prompt for _, prompt in FixtureClient.calls]
        self.assertTrue(all("Linkless" not in prompt for prompt in prompts))
        self.assertEqual(
            seen_urls(load_state(self.root / "feeds/state.json")),
            {"https://example.invalid/Valid"},
        )
        digest = next(self.root.joinpath("feeds").glob("*.md")).read_text()
        self.assertIn("https://example.invalid/Valid", digest)
        self.assertNotIn("Linkless", digest)

    def test_all_linkless_feed_stops_before_model_or_digest(self):
        missing = article("Missing")
        missing["url"] = ""
        blank = article("Blank")
        blank["url"] = "   "
        self.run_pipeline([missing, blank])

        self.assertEqual(FixtureClient.calls, [])
        self.assertEqual(list(self.root.glob("feeds/*.md")), [])

    def test_legacy_empty_url_is_dropped_without_losing_real_membership(self):
        state_path = self.root / "feeds/state.json"
        state_path.parent.mkdir()
        state_path.write_text(
            '{"processed_urls": ["", "https://example.invalid/A"], '
            '"last_run": null}'
        )
        migrated = load_state(state_path)
        self.assertEqual(
            migrated["legacy_processed_urls"], ["https://example.invalid/A"]
        )

        self.run_pipeline([article("A"), article("B")])
        persisted = load_state(state_path)
        self.assertEqual(
            seen_urls(persisted),
            {"https://example.invalid/A", "https://example.invalid/B"},
        )
        filtered_prompts = [
            prompt for _, prompt in FixtureClient.calls if "Rate each article" in prompt
        ]
        self.assertEqual(len(filtered_prompts), 1)
        self.assertNotIn('0. "A"', filtered_prompts[0])
        self.assertIn('0. "B"', filtered_prompts[0])

    def test_corrupt_existing_state_fails_instead_of_resetting(self):
        state_path = self.root / "feeds/state.json"
        state_path.parent.mkdir()
        state_path.write_text("{broken")
        with self.assertRaisesRegex(ResearchError, "Could not read research state"):
            self.run_pipeline([article("A")])
        self.assertEqual(state_path.read_text(), "{broken")

        state_path.write_text('{"last_run": null}')
        with self.assertRaisesRegex(ResearchError, "missing 'processed_urls'"):
            load_state(state_path)
        state_path.write_text(
            '{"processed_urls": [], "last_run": null, "procesed_urls": []}'
        )
        with self.assertRaisesRegex(ResearchError, "Unknown legacy"):
            load_state(state_path)

    def test_modern_history_retains_true_latest_thousand(self):
        old = [f"https://example.invalid/old-{index}" for index in range(1000)]
        state = {
            "version": 2,
            "legacy_processed_urls": [],
            "processed_urls": old,
            "last_run": None,
        }
        updated = record_completed(state, ["https://example.invalid/new"], "now")
        self.assertEqual(len(updated["processed_urls"]), 1000)
        self.assertEqual(updated["processed_urls"][0], old[1])
        self.assertEqual(updated["processed_urls"][-1], "https://example.invalid/new")

    def test_legacy_membership_is_lossless_until_known_cohort_reaches_limit(self):
        legacy = [f"https://example.invalid/legacy-{index}" for index in range(1000)]
        state_path = self.root / "feeds/state.json"
        state_path.parent.mkdir()
        state_path.write_text(
            '{"processed_urls": ['
            + ",".join(f'"{url}"' for url in legacy)
            + '], "last_run": null}'
        )
        migrated = load_state(state_path)
        first = record_completed(migrated, ["https://example.invalid/new-0"], "one")
        self.assertEqual(first["legacy_processed_urls"], legacy)
        self.assertEqual(len(seen_urls(first)), 1001)

        remaining = [f"https://example.invalid/new-{index}" for index in range(1, 1000)]
        retired = record_completed(first, remaining, "two")
        self.assertEqual(retired["legacy_processed_urls"], [])
        self.assertEqual(len(retired["processed_urls"]), 1000)
        self.assertEqual(retired["processed_urls"][0], "https://example.invalid/new-0")

    def test_same_day_append_preserves_previous_bytes(self):
        self.run_pipeline([article("A")])
        digest = next(self.root.joinpath("feeds").glob("*.md"))
        first = digest.read_bytes()
        self.run_pipeline([article("A"), article("B")])
        second = digest.read_bytes()
        self.assertTrue(second.startswith(first))
        self.assertIn(b"https://example.invalid/B", second[len(first):])
        self.assertEqual(second.count(b"## Run at "), 2)

    def test_reprocess_appends_digest_without_changing_state(self):
        self.run_pipeline([article("A")])
        state_path = self.root / "feeds/state.json"
        before = state_path.read_bytes()
        digest = next(self.root.joinpath("feeds").glob("*.md"))
        first_digest = digest.read_bytes()

        self.run_pipeline([article("B")], reprocess=True)
        self.assertEqual(state_path.read_bytes(), before)
        self.assertTrue(digest.read_bytes().startswith(first_digest))
        self.assertIn(b"https://example.invalid/B", digest.read_bytes())

    def test_atomic_digest_failure_preserves_existing_file(self):
        output = self.root / "feeds/2026-09-11.md"
        output.parent.mkdir()
        original = b"existing bytes without newline"
        output.write_bytes(original)
        analyzed = {
            **article("A"),
            "summary": "Summary",
            "key_insight": "Insight",
            "relevance": "Relevant",
            "tags": "test",
        }
        with patch(
            "scripts.research_assistant.output.os.replace",
            side_effect=OSError("simulated replace failure"),
        ):
            with self.assertRaises(OSError):
                write_digest(output, [analyzed], "- Theme", "2026-09-11")
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(list(output.parent.glob(".2026-09-11.md.*.tmp")), [])

    def test_atomic_state_failure_preserves_existing_file(self):
        state_path = self.root / "feeds/state.json"
        initial = record_completed(load_state(state_path), ["https://example.invalid/A"], "one")
        save_state(state_path, initial)
        original = state_path.read_bytes()
        updated = record_completed(initial, ["https://example.invalid/B"], "two")
        with patch(
            "scripts.research_assistant.state.os.replace",
            side_effect=OSError("simulated replace failure"),
        ):
            with self.assertRaises(OSError):
                save_state(state_path, updated)
        self.assertEqual(state_path.read_bytes(), original)
        self.assertEqual(list(state_path.parent.glob(".state.json.*.tmp")), [])

    def test_latest_five_dated_drafts_and_deterministic_fallback(self):
        drafts = self.root / "drafts"
        drafts.mkdir()
        for day in range(1, 7):
            drafts.joinpath(f"2026-09-{day:02}.md").write_text(f"Draft {day}")
        drafts.joinpath("z-undated.md").write_text("Undated")
        with patch(
            "scripts.research_assistant.context.summarize_with_ai",
            side_effect=lambda text, *args, **kwargs: text,
        ):
            context = build_context(drafts, self.root / "IDEAS.md")
        self.assertIn("Draft 6", context)
        self.assertNotIn("Draft 1", context)
        self.assertNotIn("Undated", context)

    def test_state_and_digest_are_tracked_and_workflow_is_serialized(self):
        self.root.joinpath(".gitignore").write_text(REPO.joinpath(".gitignore").read_text())
        self.root.joinpath("feeds").mkdir()
        self.root.joinpath("feeds/state.json").write_text(
            '{"version": 2, "legacy_processed_urls": [], "processed_urls": [], "last_run": null}'
        )
        self.root.joinpath("feeds/digest.md").write_text("Fixture digest")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "add", "feeds/"], cwd=self.root, check=True)
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"], cwd=self.root, text=True
        ).splitlines()
        self.assertEqual(staged, ["feeds/digest.md", "feeds/state.json"])

        workflow = REPO.joinpath(".github/workflows/research-assistant.yml").read_text()
        self.assertIn("group: research-assistant", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", workflow)
        self.assertIn('git rebase "origin/$DEFAULT_BRANCH"', workflow)


if __name__ == "__main__":
    unittest.main()
