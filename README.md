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
- Chrome with the [Claude in Chrome extension](https://chromewebstore.google.com/) for the publishing skills

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

4. Export your Anthropic API key in the terminal that will run the Research Assistant. The hidden prompt keeps the key out of your shell history.

   ```bash
   read -s ANTHROPIC_API_KEY
   export ANTHROPIC_API_KEY
   test -n "$ANTHROPIC_API_KEY" && echo "ANTHROPIC_API_KEY is set"
   ```

   To run the Research Assistant in GitHub Actions, also store the key as a repository secret. `gh secret set` prompts for the value and encrypts it before upload.

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

8. Start Claude Code from the repository.

   ```bash
   claude
   ```

   Run `/commit` when you want Claude Code to commit and sync selected vault files to the verified private `origin`.

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Anthropic API access for local runs and GitHub Actions |
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
│   └── research.yaml     # Models for each Research Assistant stage
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

### Research models

Edit the four keys under `models` in `config/research.yaml` to choose the Anthropic Claude model for each stage:

```yaml
models:
  context: claude-haiku-4-5-20251001
  filter: claude-haiku-4-5-20251001
  analysis: claude-sonnet-5
  synthesis: claude-sonnet-5
```

Both local runs and GitHub Actions read this file. Each stage key is optional. If you omit one, Mindleap uses the default value shown above. Mindleap currently supports Anthropic Claude models only and does not fall back to another model. If a configured model is unavailable or invalid, the failed stage names the `models` key to change.

### RSS feeds

Edit `config/feeds.yaml` to add your preferred RSS feeds:

```yaml
feeds:
  - name: Your Favorite Blog
    url: https://example.com/feed.xml
```

### User profile

Edit `USER.md` with:
- Your background and expertise
- Current focus areas
- Writing goals and topics

The Research Assistant uses this to filter articles relevant to you.

Name drafts `YYYY-MM-DD-title.md` so research can select the newest five reliably. Undated drafts follow dated drafts in descending filename order.

### Ideas tracking

Use `IDEAS.md` to track:
- Active ideas you're developing
- Questions you're exploring
- Backlog of future topics

Add `@Claude` mentions for tasks you want Claude to handle automatically.

## GitHub Actions

### Research Assistant

Runs daily at 5:00 AM CET:

1. Fetches configured RSS feeds
2. Filters articles based on your USER.md and IDEAS.md
3. Analyzes relevant articles with Claude
4. Writes personalized digests to `feeds/`

Each run appends a timestamped section to that day's digest. If a stage fails, the Research Assistant leaves its state unchanged so a later run can retry the same articles. `--reprocess` also leaves the state unchanged and appends another run section. The state file preserves legacy URLs in their existing unknown order until it has recorded 1,000 new completions in chronological order.

To enable:

1. Push your configuration and notes to the private `origin` created above
2. Add `ANTHROPIC_API_KEY` to repository secrets
3. The workflow runs automatically or can be triggered manually

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## License

MIT License - see [LICENSE](LICENSE) for details.
