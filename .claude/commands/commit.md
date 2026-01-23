---
description: Stage all changes, commit with message, and push to remote
---

# Git Commit and Push

Stage all changes, generate a commit message, and push to remote.

## Steps

1. Run `git status` to see what changed
2. Run `git diff` to understand the changes
3. Stage all changes: `git add -A`
4. Generate a concise commit message based on the changes
5. Commit: `git commit -m "<generated message>"`
6. Push to remote: `git push`

## Commit Message Guidelines

- Keep it short (under 72 characters)
- Use imperative mood ("Add feature" not "Added feature")
- Focus on what changed, not how
- For multiple changes, summarize the main theme

## Rules

- Do NOT add "Co-Authored-By" or any Claude attribution
- Do NOT ask the user for a commit message - decide yourself
- Report success or failure with the commit hash
