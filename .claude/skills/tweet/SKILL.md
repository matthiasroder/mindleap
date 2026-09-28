---
name: tweet
description: Create a tweet from the last discussed idea and publish it to X/Twitter. Use when the user wants to create and post social media content from a conversation topic.
---

# Tweet Skill

## Purpose

Transforms the most recently discussed idea, article draft, or topic into tweet-ready content and publishes it to X/Twitter using browser automation. No file saving - everything happens in conversation and browser.

## Trigger Phrases

- "/tweet"
- "Create a tweet from this"
- "Turn this into a tweet"
- "Make this tweetable"
- "Post this to X"

## Requirements

- Chrome browser with the Claude in Chrome extension and a connected Claude Code session (`claude --chrome` or enable via `/chrome`)
- Claude Code signed in with `/login` using a supported Claude plan; API-key authentication alone does not support Chrome integration
- User must be logged into X/Twitter

## Process

### When invoked:

1. **Identify the last discussed idea**
   - Look at the recent conversation context
   - Find the main topic, article draft, concept, or insight being discussed
   - If a draft file was recently created or referenced, use that as the source

2. **Extract the core message**
   - What is the key insight or provocative angle?
   - What would spark discussion or debate?
   - What is counterintuitive or challenges conventional thinking?

3. **Create 3 tweet options**

   **Option A - Provocative**: Start with a bold claim or challenge ("Most people get this wrong...")

   **Option B - Question-led**: Open with a thought-provoking question that invites engagement

   **Option C - Short & Sharp**: Maximum impact in minimum words (under 280 characters)

4. **Present options to user**
   - Display all three options in the conversation
   - Include hashtag suggestions
   - Ask: "Which one should I post? (A, B, or C)"
   - Wait for user to pick an option

5. **Browser automation**
   - Call `tabs_context_mcp` with `createIfEmpty: true` to get/create tab
   - Navigate to `https://x.com`
   - Wait for page to load
   - Click on "What's happening?" compose box
   - Type the chosen tweet content

6. **Check character count**
   - Look for the character counter near the Post button
   - If negative (over limit), inform user and offer to trim
   - Common trimming strategy: remove hashtags first, then tighten copy
   - Re-type trimmed version if needed

7. **Confirm before posting**
   - Take a screenshot showing the composed tweet
   - Ask user: "Tweet is ready. Should I click Post?"
   - Wait for explicit confirmation ("yes", "post it", etc.)
   - Only click Post after confirmation

8. **Post and confirm**
   - Click the Post button
   - Wait for the tweet to appear in the feed
   - Take a screenshot confirming it was posted
   - Report success to user

## Tweet Style Guidelines

For effective tweets:
- Be direct and confident, avoid hedging
- Challenge conventional thinking when appropriate
- Focus on practical insights over abstract theory
- Eliminate filler words and fluff
- Avoid corporate jargon
- Lead with the most interesting point

## Character Limit Handling

Standard X accounts: 280 characters
Premium accounts: longer posts allowed

If over the limit:
1. First try removing some hashtags
2. Then tighten the copy (remove filler words)
3. Always confirm trimmed version with user before posting

## Hashtag Guidelines

Keep hashtags relevant and minimal:
- 3-5 hashtags maximum
- Place at the end of the tweet
- Use hashtags relevant to your content and audience
- Remove lower-priority hashtags first when trimming

## Output Format

When presenting options, use this format:

```
**Option A (Provocative)**
[Bold opening claim with supporting points]

**Option B (Question-led)**
[Thought-provoking question with key insight]

**Option C (Short & Sharp)**
[Maximum impact, under 280 chars]

**Suggested hashtags:** #AI #Tech [relevant tags]

Which one should I post? (A, B, or C)
```

## Examples

**Context**: Just discussed an article about AI agents and thinking loops

**Options presented**:
- Option A: "Most people use AI wrong. They ask, receive, move on..."
- Option B: "What if AI wasn't for getting answers—but refining questions?"
- Option C: "The future of AI isn't ask-and-receive. It's think-together."

**User says**: "Option C"

**Action**: Opens browser, navigates to X, composes Option C, takes screenshot, confirms, posts.
