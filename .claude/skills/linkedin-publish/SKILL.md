---
name: linkedin-publish
description: Prepare a LinkedIn newsletter article in the browser for the user to review and publish. Use when asked to publish or share a draft on LinkedIn.
---

# LinkedIn Publish Skill

## Purpose

Publishes a blog post to your LinkedIn newsletter and prepares it for final review before publishing.

## Trigger Phrases

- "/linkedin-publish"
- "Publish this to LinkedIn"
- "Post to LinkedIn newsletter"
- "Share on LinkedIn"

## Requirements

- Chrome browser with the Claude in Chrome extension and a connected Claude Code session (`claude --chrome` or enable via `/chrome`)
- Claude Code signed in with `/login` using a supported Claude plan; API-key authentication alone does not support Chrome integration
- User must be logged into LinkedIn

## Process

### When user wants to publish to LinkedIn:

1. **Identify the file to publish**
   - If a specific file is mentioned, use that
   - If no file specified, use the most recent file in `published/`
   - Files typically have frontmatter with title and content

2. **Extract and prepare content**
   - Get title from frontmatter `title:` field or derive from filename
   - Extract body content (everything after the frontmatter `---` markers)
   - Strip any remaining metadata sections
   - Convert markdown links `[text](url)` to plain text with URL (LinkedIn auto-links)
   - Remove markdown italic markers (LinkedIn doesn't render them)
   - IMPORTANT: Use SINGLE newlines between paragraphs, not double. Double newlines create excessive spacing in LinkedIn's editor.

3. **Browser automation**
   - Call `tabs_context_mcp` with `createIfEmpty: true` to get/create tab
   - Navigate to `https://www.linkedin.com`
   - Wait for page to load
   - Click "Write article" button
   - Click on Title field and type the title
   - Click on content area and type the prepared content (single newlines!)
   - Click "Next" button to open publish dialog

4. **Generate announcement text**
   - Write a compelling 2-3 sentence teaser summarizing the article's key value
   - Generate 5-6 relevant hashtags based on the article's themes
   - Format: teaser text, blank line, hashtags
   - Click in the announcement text field and type the teaser

5. **Hand over to user**
   - Do NOT click Publish
   - Tell the user: "LinkedIn is ready. The publish dialog is open with your announcement text. Find the browser window to review, edit, and publish."

## Content Formatting Rules

LinkedIn's article editor requires specific formatting:

```
Paragraph one text here.
Paragraph two text here.
Paragraph three text here.
```

NOT:

```
Paragraph one text here.

Paragraph two text here.

Paragraph three text here.
```

The double newlines create empty paragraph blocks that look like excessive whitespace.

## Newsletter

Publishes to your LinkedIn newsletter (select in the publish dialog).

## Cover Images

Skip cover images. The user can add one manually if desired.

## Examples

**User**: "/linkedin-publish"
1. Find most recent file in `published/`
2. Extract title and content
3. Open LinkedIn, create article
4. Fill in content with proper formatting
5. Click Next, add teaser with hashtags
6. Tell user: "LinkedIn is ready. Find the browser window to review, edit, and publish."

**User**: "/linkedin-publish published/2026-01-19_my-post.md"
1. Read the specified file
2. Follow same process as above

## Output

Always end with:
- Confirmation that the draft is ready
- Reminder that the publish dialog is open
- Instruction to find the browser window and review/edit/publish
