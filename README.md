# Mindleap

A Markdown knowledge vault with Claude Code skills for research, idea extraction, and social publishing.

## Features

- The Research Assistant analyzes RSS feeds each day and filters articles against your interests and current work.
- The idea extraction skill mines your notes for ideas worth developing.
- The publishing skills prepare content for X and LinkedIn.
- The `/commit` command commits and syncs selected vault files to a private GitHub repository.

## Prerequisites

- [Git](https://git-scm.com/) and a GitHub account
- [GitHub CLI](https://cli.github.com/) authenticated with `gh auth login`
- A Markdown editor such as [Obsidian](https://obsidian.md/)
- [Claude Code](https://claude.ai/claude-code) CLI
- Python 3.11 or later for the Research Assistant
- For publishing: a supported Claude plan, Claude Code signed in with `/login`, and Chrome with the [Claude in Chrome extension](https://code.claude.com/docs/en/chrome)

## Create your private vault

1. Clone the public source repository.

   ```bash
   git clone https://github.com/matthiasroder/mindleap.git
   cd mindleap
   ```

2. Create a standalone private repository before you add personal information.

   ```bash
   git remote rename origin upstream
   gh auth status
   gh repo create mindleap-vault --private --source=. --remote=origin
   gh repo set-default origin
   git remote get-url --push --all origin
   gh repo view --json nameWithOwner,visibility --jq '"\(.nameWithOwner) \(.visibility)"'
   ```

   The URL must name your new personal repository. The last command must show the same owner and repository followed by `PRIVATE`. Stop if it shows `PUBLIC` or a repository you do not own. GitHub does not let you make a public fork private, so the command above creates a separate repository instead of a fork.

3. Push the unmodified source to the verified private repository.

   ```bash
   git push -u origin main
   ```

4. For local research, read the API key for your selected provider into a shell variable. The hidden prompt keeps the key out of your shell history. The variable is intentionally not exported to Claude Code: research API access and Claude account login are separate.

   ```bash
   read -r -s MINDLEAP_RESEARCH_KEY
   test -n "$MINDLEAP_RESEARCH_KEY" && echo "Research key is set for this terminal session"
   ```

   To run the Research Assistant in GitHub Actions, also store the key as a repository secret. Use `ANTHROPIC_API_KEY` for Anthropic, `OPENAI_API_KEY` for OpenAI, or `LLM_API_KEY` for an OpenAI-compatible endpoint. Set every secret needed if stages use different providers. `gh secret set` prompts for the value and encrypts it before upload.

   ```bash
   gh secret set ANTHROPIC_API_KEY
   ```

   Do not put API keys in `config/research.yaml` or another tracked file.

5. Create a virtual environment and install the Python dependencies for the Research Assistant.

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r scripts/research_assistant/requirements.txt
   ```

6. Add your profile only after you verify the private `origin` in step 2.

   ```bash
   cp USER.md.example USER.md
   ```

   Edit `USER.md` and `IDEAS.md`, and add private notes under `drafts/`.

7. Open the `mindleap` directory in your Markdown editor.

8. Start Claude Code from the repository. Use `/login` to sign in with your Claude account. If your shell already exports an API key, omit it for this session:

   ```bash
   env -u ANTHROPIC_API_KEY claude
   ```

   Run `/commit` when you want Claude Code to commit and sync selected vault files to the verified private `origin`.

### Run research locally

With the virtual environment active and the research key entered as above:

```bash
ANTHROPIC_API_KEY="$MINDLEAP_RESEARCH_KEY" python -m scripts.research_assistant.main
```

This passes the key only to the research process. Replace `ANTHROPIC_API_KEY` with `OPENAI_API_KEY` or `LLM_API_KEY` if you selected that provider. For mixed providers, export all selected keys. A new terminal session needs the key entered again. `.env.example` lists the variable names; the Python script does not automatically load `.env` files.

### Connect browser publishing

Research uses the configured LLM API; the X and LinkedIn skills use your logged-in browser. Chrome integration needs a supported Claude plan and Claude Code `/login`, and does not work with API-key-only authentication.

1. Install the [Claude in Chrome extension](https://code.claude.com/docs/en/chrome) and sign in to the browser accounts you want to use.
2. Launch `env -u ANTHROPIC_API_KEY claude --chrome` from the vault.
3. Run `/chrome` and check that the integration is enabled and the extension is installed. You can enable it by default there.
4. Invoke `/tweet` or `/linkedin-publish`. Each skill prepares the content for your review before publication.

### Claude settings

Shared defaults live in `.claude/settings.json`. Personal changes belong in the ignored `.claude/settings.local.json`. The template does not pre-approve all shell commands. If you choose to allow Bash commands broadly, make that choice in your own local settings; the template works with normal permission prompts.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | If selected | Anthropic API access for local runs and GitHub Actions |
| `OPENAI_API_KEY` | If selected | OpenAI API access |
| `LLM_API_KEY` | If selected | API key for an OpenAI-compatible endpoint; for a local endpoint without authentication, use a placeholder value |
| `PERPLEXITY_API_KEY` | Optional | For Perplexity MCP tools |

## Directory structure

```
mindleap/
├── .claude/              # Claude Code configuration
│   ├── commands/         # Slash commands (/commit)
│   └── skills/           # Complex workflows
├── .github/workflows/    # GitHub Actions (Research Assistant)
├── config/               # Configuration files
│   ├── feeds.yaml        # RSS feeds for Research Assistant
│   └── research.yaml     # Provider and models for each Research Assistant stage
├── scripts/              # Automation scripts
│   └── research_assistant/
├── drafts/               # Work in progress content
├── published/            # Finalized content
├── done/                 # Completed but not published
├── abandoned/            # Shelved ideas
├── ideas/                # Extracted ideas and concepts
├── feeds/                # Research Assistant digests
├── knowledge/            # Reference material
├── IDEAS.md              # Active ideas and questions
├── USER.md               # Your profile and interests
└── CLAUDE.md             # Instructions for Claude
```

## Skills reference

| Skill | Trigger | Description |
|-------|---------|-------------|
| `/sync` | Manual | Pull changes, read key files, check for @Claude todos |
| `/commit` | Manual | Stage, commit, and push changes |
| `/idea-extraction` | Manual | Extract ideas from notes or conversation |
| `/tweet` | Manual | Create and publish a tweet from recent discussion |
| `/linkedin-publish` | Manual | Publish content to LinkedIn newsletter |

## Customization

### Research provider and models

Edit `config/research.yaml` to choose the provider and model for each stage. The template defaults to Anthropic:

```yaml
provider: anthropic
models:
  context: claude-haiku-4-5-20251001
  filter: claude-haiku-4-5-20251001
  analysis: claude-sonnet-5
  synthesis: claude-sonnet-5
```

Set `provider: openai` and replace all four model IDs to use OpenAI. For an OpenAI-compatible Chat Completions API, set `provider: openai-compatible`, add `base_url: https://your-provider.example/v1`, and replace all four model IDs. An OpenAI-compatible endpoint must support `/chat/completions`, the `max_tokens` request field, and standard `choices[0].message.content` and `finish_reason` response fields.

You can route an individual stage to a different provider:

```yaml
provider: anthropic
models:
  context: claude-haiku-4-5-20251001
  filter: claude-haiku-4-5-20251001
  analysis:
    provider: openai
    model: your-openai-model-id
  synthesis:
    provider: openai-compatible
    base_url: https://your-provider.example/v1
    model: your-provider-model-id
```

Both local runs and GitHub Actions read this file. With the default Anthropic provider, omitted stages use the template defaults. If you change the default provider, specify all four models to avoid carrying over Claude model IDs. API keys belong in environment variables or GitHub secrets, never in this file. A configured provider or model failure stops the run without falling back.

### RSS feeds

Edit `config/feeds.yaml` to add your preferred RSS feeds:

```yaml
feeds:
  - name: Your Favorite Blog
    url: https://example.com/feed.xml
    max_articles: 50
```

Only the first 50 entries of each feed are considered by default, so an archive feed cannot trigger thousands of model calls on the first run. Set `max_articles` per feed to change that limit; use feeds that list their newest entries first. Feed and article URLs must use HTTP(S) and resolve to public addresses.

### User profile

Edit `USER.md` with:
- Your background and expertise
- Current focus areas
- Writing goals and topics

The Research Assistant uses this to filter articles relevant to you.

Name drafts `YYYY-MM-DD-title.md` so research can select the newest five reliably. Undated drafts follow dated drafts in descending filename order.

### Extracted ideas and research

The idea-extraction skill creates dated notes in `ideas/` with this frontmatter:

```yaml
---
research: true
---
```

Research includes the newest five opted-in idea files along with your profile, `IDEAS.md`, and five drafts. Add the same frontmatter to existing ideas you want included. Set `research: false` to retire an idea from research; files without the flag are excluded. Dates in filenames determine order consistently in local runs and GitHub Actions.

### Ideas tracking

Use `IDEAS.md` to track:
- Active ideas you're developing
- Questions you're exploring
- Backlog of future topics

Write tasks as unchecked items such as `- [ ] @Claude Review the article outline`. `/sync` finds these in `USER.md` and `IDEAS.md`; completed items and instructional mentions are ignored. Sync is manual and stops if Git cannot pull safely.

## GitHub Actions

### Research Assistant

When enabled, runs daily at 04:00 UTC (05:00 CET / 06:00 CEST):

1. Fetches configured RSS feeds
2. Filters articles based on your USER.md and IDEAS.md
3. Downloads readable text for relevant links, then analyzes that text with Claude
4. Writes personalized digests to `feeds/`

RSS headlines and previews are used for the first relevance pass only. Analysis uses up to 30,000 characters of retrieved article text. Unsupported formats such as PDFs, failed downloads, and pages yielding fewer than 80 readable words become clearly labeled link-only entries, with no generated article summary or contribution to themes. This includes many login and teaser pages. Extraction can return an excerpt; the model is instructed to stay within the supplied evidence. Link-only entries count as processed; use `--reprocess` to try retrieval again. Downloads have a 20-second socket timeout and a 5 MB response limit.

Each run appends a timestamped section to that day's digest. Feed failures and model-stage failures stop the run without advancing history. A valid empty feed is allowed; a broken feed is reported as a failure, not as “no new articles.” Fix or remove a consistently unavailable URL in `config/feeds.yaml` before retrying.

Local runs are locked against overlap. If saving a completed run is interrupted, its local recovery journal lets the next invocation finish that run and exit without making model calls or duplicating its digest section. Keep `feeds/.pending-run.json` until recovery succeeds. The lock and journal are ignored by Git; they recover local interruptions, not deleted GitHub runners. GitHub Actions publishes the digest and history together in one commit.

`--reprocess` deliberately adds another digest section without changing history. A pending interrupted run is always recovered first, even when `--reprocess` is supplied. The state file preserves legacy URLs in their existing unknown order until it has recorded 1,000 new completions in chronological order.

To enable:

1. Push your configuration and notes to the private `origin` created above
2. Add the selected provider key(s) to repository secrets (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `LLM_API_KEY`)
3. Test a manual run from the repository's Actions page
4. Enable daily runs with `gh variable set RESEARCH_ENABLED --body true`

Scheduled research is off until that repository variable is set. No API key belongs in the public template. Manual runs check for the secret and explain how to configure it if it is missing.

## Validation

After installing the Python dependencies, run:

```bash
python -m unittest discover -s tests -v
bash -n scripts/sync.sh
```

These checks require no API keys or live network access. The validation workflow runs them on pushes and pull requests with Python 3.11 and 3.13, including checks for skill filenames and metadata, settings, article retrieval, and interrupted-run recovery.

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## License

MIT License - see [LICENSE](LICENSE) for details.
