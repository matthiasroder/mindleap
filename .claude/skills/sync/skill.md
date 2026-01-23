---
name: sync
description: Pull latest changes, read key files, and check for @Claude todos. Use to manually trigger the session startup sequence.
---

# Sync Skill

## Purpose

Re-runs the vault synchronization that normally happens at session start:
1. Pulls latest git changes
2. Reads README, USER, and IDEAS files
3. Detects any @Claude todos for immediate action

## Trigger Phrases

- "/sync"
- "Sync the vault"
- "Check for updates"

## Process

Execute the sync script:

```bash
bash scripts/sync.sh
```

After running, if any @Claude todos are found, complete them immediately before proceeding with other tasks.

## When to Use

- After making changes in Obsidian that Claude should know about
- When you suspect files have been updated externally
- To refresh context on README/USER/IDEAS content
- To check if new @Claude tasks have been added
