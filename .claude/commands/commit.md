---
description: Commit selected changes and push to a reviewed remote
---

# Commit selected changes

Commit only the files that belong to the current request. Push to `origin` after you review the destination and the user's intent.

## Steps

1. Read the current request and identify the exact files that belong in the commit. Determine whether the user asked for a local commit, a private sync, or a public push.
2. Inspect both unstaged and staged changes.

   ```bash
   git status --short
   git diff
   git diff --cached
   ```

3. Check the selected paths for ignored files.

   ```bash
   git check-ignore -v --no-index -- <path>...
   ```

   Exclude every path that this command reports. Never use `git add -f`.

4. Stage each selected path explicitly.

   ```bash
   git add -- <path>...
   ```

   Never use `git add -A`, `git add .`, or another blanket path.

5. Review the exact staged paths and their content.

   ```bash
   git diff --cached --name-status
   git diff --cached
   ```

   If the staged changes include an unrelated path or hunk, unstage that path and stage only the intended content. Repeat the review before you commit.

6. Inspect every push destination before you commit.

   ```bash
   git remote get-url --push --all origin
   gh repo view "<push-url>" --json nameWithOwner,visibility --jq '"\(.nameWithOwner) \(.visibility)"'
   ```

   Run `gh repo view` for each URL from the first command. Treat a destination as unverified if `origin` is missing or either command fails.

7. Generate a concise commit message and commit the staged changes.

   ```bash
   git commit -m "<generated message>"
   ```

8. Apply the push rule that matches the reviewed destination and the current request.

   - If every push destination is verified as private, push without another approval when the current request already authorizes private sync.
   - If the user asked for a local commit, do not push.
   - For any public or unverified destination, proceed only if the current request specifically approves that destination. Otherwise, show every destination, its visibility result, the staged path list, and the branch, then ask for approval before you push.

   ```bash
   git push origin HEAD
   ```

## Commit message guidelines

- Keep the subject under 72 characters.
- Use the imperative mood, such as `Add private vault setup`.
- Describe what changed.
- Summarize the main theme when the commit contains several related files.

## Rules

- Do not add `Co-Authored-By` or other Claude attribution.
- Decide the commit message from the staged diff. Do not ask the user to write it.
- Report the commit hash and whether the push succeeded, failed, or was skipped.
