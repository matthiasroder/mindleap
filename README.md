# Mindleap

A markdown-based knowledge vault with Claude Code skills for automated research, idea extraction, and social publishing.
## Features

- **Automated Research Assistant**: Daily RSS feed analysis that filters articles based on your interests and current work
- **Idea Extraction**: Mine your notes for ideas worth developing
- **Social Publishing**: Streamlined workflows for Twitter/X and LinkedIn
- **Git-based Sync**: Version control your knowledge with automatic commits

## Prerequisites

- Markdown editor like [Obsidian](https://obsidian.md/) (for viewing and editing the vault)
- [Claude Code](https://claude.ai/claude-code) CLI
- Python 3.11+ (for Research Assistant)
- Chrome with [Claude-in-Chrome extension](https://chromewebstore.google.com/) (for publishing skills)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mindleap.git
   cd mindleap
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Install Python dependencies** (for Research Assistant)
   ```bash
   pip install -r scripts/research_assistant/requirements.txt
   ```

4. **Configure your profile**
   ```bash
   cp USER.md.example USER.md
   # Edit USER.md with your information
   ```

5. **Open in Markdown editor **

6. **Start Claude Code**
   ```bash
   claude
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | For Research Assistant GitHub Action |
| `PERPLEXITY_API_KEY` | Optional | For Perplexity MCP tools |

## Directory Structure

```
mindleap/
├── .claude/              # Claude Code configuration
│   ├── commands/         # Slash commands (/commit)
│   └── skills/           # Complex workflows
├── .github/workflows/    # GitHub Actions (Research Assistant)
├── config/               # Configuration files
│   └── feeds.yaml        # RSS feeds for Research Assistant
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

## Skills Reference

| Skill | Trigger | Description |
|-------|---------|-------------|
| `/sync` | Manual | Pull changes, read key files, check for @Claude todos |
| `/commit` | Manual | Stage, commit, and push changes |
| `/idea-extraction` | Manual | Extract ideas from notes or conversation |
| `/tweet` | Manual | Create and publish a tweet from recent discussion |
| `/linkedin-publish` | Manual | Publish content to LinkedIn newsletter |

## Customization

### RSS Feeds

Edit `config/feeds.yaml` to add your preferred RSS feeds:

```yaml
feeds:
  - name: Your Favorite Blog
    url: https://example.com/feed.xml
```

### User Profile

Edit `USER.md` with:
- Your background and expertise
- Current focus areas
- Writing goals and topics

The Research Assistant uses this to filter articles relevant to you.

### Ideas Tracking

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

To enable:
1. Push this repo to GitHub
2. Add `ANTHROPIC_API_KEY` to repository secrets
3. The workflow runs automatically or can be triggered manually

## Contributing

Contributions welcome! Please open an issue or submit a PR.

## License

MIT License - see [LICENSE](LICENSE) for details.
