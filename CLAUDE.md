# CLAUDE.md

This file provides guidance to Claude Code on how to work with this vault.

## What This Is

This is an **Obsidian vault** - a personal knowledge management system. It is not a software project with build systems or tests.

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

- `/commit` - Stage all changes, commit with message, and push to remote
- `/idea-extraction` - Extract ideas from documents and save to /ideas
- `/linkedin-publish` - Publish content to LinkedIn newsletter (opens browser)
- `/sync` - Pull latest changes, read key files, check for @Claude todos
- `/tweet` - Create a tweet from recent discussion and publish to X/Twitter

## Workflows and GitHub Actions

### Research Assistant
1. Runs daily at 5:00 CET
2. Fetches RSS feeds from `config/feeds.yaml`
3. Filters articles for relevance (based on IDEAS.md, USER.md, drafts)
4. Analyzes and summarizes relevant articles
5. Writes personalized digests to `feeds/YYYY-MM-DD.md`
