# CLAUDE.md

This file provides guidance to Claude Code on how to work with this directory.

## What This Is

This is a personal knowledge management system with a Python research assistant. Its offline regression tests run with `python -m unittest discover -s tests -v` after installing `scripts/research_assistant/requirements.txt`.

## Rules

**Session Start Behavior:**
When a session starts and the user calls /sync:
1. Output a one-line sync acknowledgment (e.g., "Vault synced. 1 @Claude todo found.")
2. If @Claude todos were detected, address them IMMEDIATELY - do not wait for user input
3. After addressing todos (or if none exist), wait for user input

**Guidelines:**
1. Use `[[wikilinks]]` for internal note connections
2. Use `/drafts` for brainstorming and content creation
3. Preserve existing link structures when editing

## Directory Structure

```
mindleap/
├── drafts/        # Work in progress
├── published/     # Finalized content
├── done/          # Completed but not published
├── abandoned/     # Shelved ideas
├── ideas/         # Extracted ideas
├── feeds/         # Research digests
├── knowledge/     # Reference material
├── IDEAS.md       # Active ideas and questions
└── USER.md        # User profile and interests
```

## Available Tools

### Model Context Protocols (MCPs)

If Perplexity MCP is configured:
- `mcp__perplexity__perplexity_ask` - Quick questions and conversations
- `mcp__perplexity__perplexity_research` - Deep research with citations
- `mcp__perplexity__perplexity_search` - Web search with ranked results
- `mcp__perplexity__perplexity_reason` - Complex reasoning tasks

## Available Skills / Commands

Skills and commands are invoked with `/skillname` or triggered by context:

- `/commit` - Review the destination and changes, stage intended paths, commit, and push after the required privacy check
- `/idea-extraction` - Extract ideas from documents and save to /ideas
- `/linkedin-publish` - Publish content to LinkedIn newsletter (opens browser)
- `/sync` - Pull latest changes, read key files, check for @Claude todos
- `/tweet` - Create a tweet from recent discussion and publish to X/Twitter

## Workflows and GitHub Actions

### Research Assistant
1. Runs at 04:00 UTC when the private vault's `RESEARCH_ENABLED` variable is `true`
2. Fetches RSS feeds from `config/feeds.yaml`
   Uses the four model choices in `config/research.yaml`
3. Filters articles for relevance (based on IDEAS.md, USER.md, five drafts, and five idea files with `research: true`)
4. Retrieves article text before analysis; unavailable sources are listed as links without invented summaries
5. Appends each completed run to `feeds/YYYY-MM-DD.md`
6. Records completed URLs in tracked `feeds/state.json`; failed feed/model stages leave history unchanged
7. Serializes local runs and recovers interrupted saves from ignored `feeds/.pending-run.json` before starting new work

`--reprocess` adds another digest section without changing history. Keep the personal vault in a private repository before adding a profile, notes, or research output.

Claude account login and browser publishing are separate from research API authentication. Launch `env -u ANTHROPIC_API_KEY claude --chrome` for publishing and use `/login` and `/chrome` to connect. Shared settings are in `.claude/settings.json`; personal overrides belong in ignored `.claude/settings.local.json`.
