---
name: idea-extraction
description: Extract and assess ideas from source material (notes, drafts, folders), producing a structured ideas document with novelty assessments and connections to current work. Use when asked to mine content for ideas, find what's worth developing, or extract insights from existing material.
---

# Idea Extraction Skill

## Purpose

Extracts candidate ideas from source material and produces a structured ideas document with novelty assessments, connections to current work, and recommendations for what to develop further.

**Output:** An ideas document saved to `/ideas/` — NOT a full draft article.

## Trigger Phrases

- "/idea-extraction"
- "Extract ideas from [source]"
- "What ideas are in these notes?"
- "Mine this for ideas"
- "Find the ideas worth developing"
- "What's extractable from [source]?"

## Inputs

**Required:** Source material (one of):
- A specific file path
- A folder path
- "Recent conversation" / conversation context
- "My IDEAS.md"

**Optional:** Focus area or theme to filter by

## Process

### Step 1: Identify & Read Source

- If file path → read it directly
- If folder → scan with Glob/Read and process relevant files
- If "conversation" → extract key themes from recent discussion
- If "IDEAS.md" → read `IDEAS.md` in the vault root

### Step 2: Extract Candidate Ideas

For each idea found, extract:
- **Title/Label** — short descriptive name
- **Source** — file path, line reference, or context
- **Core claim** — what the idea actually asserts or proposes
- **Open questions** — what remains unresolved or worth exploring

### Step 3: Assess Novelty

For each idea, evaluate three dimensions:
- **Internal:** Is this developed or dormant in the vault? Check existing notes, drafts, and `/ideas/` folder.
- **To current work:** Does it connect to recent drafts in `/drafts/`, active projects, or `IDEAS.md`?
- **To discourse:** Fresh framing or well-trodden ground? Is this a new angle on an existing debate?

Use these labels:
- Internal: `developed` | `dormant` | `new`
- To current work: describe the connection or `none`
- To discourse: `fresh` | `derivative` | `standard`

### Step 4: Find Connections

- Link to related vault content using `[[wikilinks]]`
- Read `IDEAS.md` to find connections
- Scan `/drafts/` for relevant work-in-progress
- Identify which ideas could combine into something larger

### Step 5: Write Ideas Document

Save to `/ideas/YYYY-MM-DD-[source-name]-extraction.md` with the structure below.

Prefix every new filename with the extraction date (`YYYY-MM-DD-`), then use a descriptive, hyphenated source name:
- From a file: `YYYY-MM-DD-[filename]-extraction.md`
- From a folder: `YYYY-MM-DD-[foldername]-extraction.md`
- From conversation: `YYYY-MM-DD-[topic]-extraction.md`

Each new extraction includes `research: true` frontmatter. The Research Assistant reads the newest five opted-in idea files. Explain that the user can set `research: false` to exclude an extraction. Preserve the existing setting when updating a document. All `/ideas/`, `/drafts/`, and similar paths in this skill refer to folders inside the vault, not the filesystem root.

### Step 6: Report to User

- Confirm file saved with path
- Highlight top 3-5 most promising ideas with brief rationale
- Suggest specific next steps (which to develop, what to research)

## Output Template

```markdown
---
research: true
---

# Idea Extraction: [Source Name]

Extracted from: [source path or description]
Date: [YYYY-MM-DD]

---

## Summary

- **Total ideas extracted:** X
- **Highly novel:** X
- **Developed but dormant:** X
- **Connected to current work:** X

---

## Ideas

### 1. [Idea Title]

**Source:** [[path/to/source]] or conversation context

**Core Claim:**
[What the idea asserts or proposes]

**Open Questions:**
- [Question 1]
- [Question 2]

**Novelty Assessment:**
- *Internal:* [developed/dormant/new]
- *To current work:* [connection description or "none"]
- *To discourse:* [fresh/derivative/standard]

---

### 2. [Next Idea Title]

**Source:** [[path/to/source]]

**Core Claim:**
[What the idea asserts]

**Open Questions:**
- [Question]

**Novelty Assessment:**
- *Internal:* [status]
- *To current work:* [connection]
- *To discourse:* [assessment]

---

[Continue for all extracted ideas...]

---

## Connections to Current Work

| Idea | Connects To | How |
|------|-------------|-----|
| [Idea title] | [[current draft or project]] | [Brief description of connection] |
| [Idea title] | [[IDEAS]] item | [How they relate] |

---

## Suggested Next Steps

1. **[Most promising idea]** → develop into [format: blog post, thread, research note]
2. **[Idea needing research]** → investigate [specific topic or question]
3. **[Ideas that combine]** → explore synthesis of [idea A] + [idea B]
```

## Grouping Guidelines

When extracting many ideas (10+), group them by theme:

```markdown
## A. [Theme Name] Ideas

### 1. [Idea]
...

### 2. [Idea]
...

---

## B. [Another Theme] Ideas

### 3. [Idea]
...
```

Common groupings:
- By domain (AI, creativity, business, personal)
- By type (frameworks, product concepts, research questions, personal insights)
- By maturity (developed, nascent, fragmentary)

## Output

When complete, provide:
1. Confirmation: "Saved extraction to `/ideas/[filename].md`"
2. Summary statistics
3. Top 3-5 ideas highlighted with one-line rationale each
4. Specific recommendations for next steps

## Examples

**Input:** "/idea-extraction on the old_notes folder"

**Output:** Creates `/ideas/YYYY-MM-DD-old-notes-extraction.md` with ideas grouped by theme, each with novelty assessment and connections to current work.

---

**Input:** "Extract ideas from our conversation about creativity research"

**Output:** Creates `/ideas/YYYY-MM-DD-creativity-research-extraction.md` with ideas discussed, noting which connect to existing drafts and which are novel angles worth developing.

---

**Input:** "Mine /drafts/ for ideas worth a Twitter thread"

**Output:** Creates `/ideas/YYYY-MM-DD-drafts-extraction.md` focusing on tweetable concepts, with recommendations for which ideas are most suited to short-form content.
