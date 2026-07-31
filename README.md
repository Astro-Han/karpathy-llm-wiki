# karpathy-llm-wiki

**A reusable skill for building Karpathy-style LLM wikis with Claude Code, Cursor, Codex, and other Agent Skills tools.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Astro-Han/karpathy-llm-wiki?style=social)](https://github.com/Astro-Han/karpathy-llm-wiki)
[![GitHub forks](https://img.shields.io/github/forks/Astro-Han/karpathy-llm-wiki?style=social)](https://github.com/Astro-Han/karpathy-llm-wiki)
[![Agent Skills](https://img.shields.io/badge/Agent_Skills-compatible-blue)](https://agentskills.io)
[![Install](https://img.shields.io/badge/Install-npx_add--skill-green)](https://github.com/Astro-Han/karpathy-llm-wiki#install)

<p align="center">
  <img src="assets/karpathy-tweet.png" alt="Karpathy's tweet about LLM Wiki" width="560">
</p>

`karpathy-llm-wiki` packages [Karpathy's LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) into one installable [Agent Skills](https://agentskills.io) skill. Your coding agent ingests sources into `raw/`, compiles durable knowledge pages into `wiki/`, answers questions with citations, and lints the wiki for consistency.

## What Is an LLM Wiki?

An **LLM wiki** is a knowledge system where the LLM maintains structured wiki pages instead of re-searching raw documents on every question. New sources are compiled into durable markdown pages, cross-references are updated over time, and answers cite the wiki pages that already contain the synthesized knowledge.

This skill gives you three operations:

| Operation | What it does | Output |
|-----------|--------------|--------|
| **Ingest** | Collects a source into `raw/`, triages it, then creates or updates wiki articles — or just logs it when nothing is new | New or updated wiki pages |
| **Query** | Searches the wiki and answers with citations | Grounded answers linking to markdown pages |
| **Lint** | Checks index integrity, links, and wiki health | Auto-fixes plus reported issues |

See [SKILL.md](SKILL.md) for the full skill specification.

## LLM Wiki vs RAG

| Approach | Knowledge lives in | When synthesis happens | Good for |
|----------|--------------------|------------------------|----------|
| **RAG** | Raw chunks and embeddings | At query time | Broad retrieval across large corpora |
| **LLM Wiki** | Curated markdown pages | During ingest and maintenance | Compounding knowledge, summaries, and durable cross-links |

This skill is optimized for the wiki model: knowledge that improves over time instead of re-deriving relationships on every query.

## Usage Stats

Based on a production knowledge base maintained daily since April 2026:

- **94** wiki articles across **13** topic directories
- **99** source materials ingested
- **87** operation log entries in the last 7 days

See [examples/](examples/) for sample wiki pages, source files, and operation logs.

## Install

```bash
npx add-skill Astro-Han/karpathy-llm-wiki
```

Works with any tool that supports the [Agent Skills](https://agentskills.io) standard.

## Quick Start

### 1. Ingest your first source

Give the skill a URL, a file, or pasted text:

> "Ingest this article: https://example.com/attention-is-all-you-need"

The skill stores the source in `raw/`, then compiles or updates the right knowledge pages in `wiki/`.

### 2. Ask your wiki a question

> "What do I know about attention mechanisms?"

The skill searches the wiki and answers with citations linking back to your markdown pages.

### 3. Keep the wiki healthy

> "Lint my wiki"

Checks for broken links, missing index entries, stale cross-references, and related issues.

## How the Workflow Works

The core idea from Karpathy: the LLM maintains the wiki while the human focuses on choosing sources and asking good questions.

```text
your-project/
├── raw/            ← Immutable source material
│   └── topic/
│       └── 2026-04-03-source-article.md
├── wiki/           ← Compiled knowledge pages maintained by the LLM
│   ├── topic/
│   │   └── concept-name.md
│   ├── index.md    ← Global table of contents
│   └── log.md      ← Append-only operation log
```

Each new source can update multiple pages, strengthen cross-references, and record contradictions. That is what makes the wiki compound over time.

## Tool Compatibility

This skill follows the [agentskills.io](https://agentskills.io) open standard:

| Tool | Install method |
|------|----------------|
| Claude Code | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| Cursor | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| Codex CLI | Copy to `.agents/skills/karpathy-llm-wiki/` |
| OpenCode | `npx add-skill Astro-Han/karpathy-llm-wiki` |
| Other tools | Copy `SKILL.md`, `references/`, and `scripts/` into the tool's skill directory |

## FAQ

### What is the difference between an LLM wiki and a personal wiki?

An LLM wiki is maintained by the model. It updates summaries, cross-links, index entries, and contradictions as new material arrives. A normal personal wiki depends on manual editing.

### What sources can I ingest?

Web pages, papers, blog posts, PDFs, markdown files, text files, and pasted text. The skill converts everything into markdown under `raw/` and compiles it into `wiki/`.

### Is this production-ready?

The workflow is based on a real knowledge base with 94 articles and 99 sources maintained daily since April 2026. The repo includes examples, templates, and a design spec.

## Design Boundaries

Deliberately not built, after three months of production logs and a survey of the ecosystem (LLM Wiki v2, llm-wiki-compiler, OKF, agent-memory literature):

- **Source-hash freshness tracking** — raw/ is immutable, so hashes guard against events that cannot happen. Genuinely new information arrives as new sources through normal ingest.
- **Persisted line-number citations** — every observed fidelity error was "value absent from the source", which a whole-file grep catches. Anchors only disambiguate a failure mode that has not occurred, and the annotation friction makes agents skip the rule.
- **Numeric confidence or quality scores** — false precision with no calibration behind it. Evidence strength belongs in the prose.
- **Per-article review dates** — nobody can predict at compile time how fast a domain moves. Maintenance is driven by whole-wiki lint, not per-page timers.
- **Access-based decay** — frequently asked is not the same as true.
- **Retract / bad-source machinery** — has not happened yet. Handle it manually until it does.
- **Automatic hooks and scheduled runs** — those belong to the agent harness, not a tool-agnostic skill.
- **Vector or graph search** — at 50K–100K tokens of curated wiki, grep and read are more reliable. Add search tooling only when recall measurably degrades.
- **Typed relationship ontologies** — link semantics live in the prose around the link.
- **OKF conformance** — the spec is a v0.1 draft with a minimal tooling ecosystem. Tracked; will be revisited.
- **MCP servers, UIs, output subsystems** — outside the boundary of a tool-agnostic skill.

## Inspired By

Unofficial community implementation of the workflow from [Karpathy's LLM Wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f). The value here is the reusable workflow, prompt structure, and battle-tested knowledge-compilation rules.

See also: [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki), [atomicmemory/llm-wiki-compiler](https://github.com/atomicmemory/llm-wiki-compiler), and [Phelan164/codex-howto](https://github.com/Phelan164/codex-howto) (a Codex-focused engineering guide with a review-first wiki). We are tracking Google's [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/tree/main/okf) draft and will evaluate compatibility once the spec and tooling mature.

## License

[MIT](LICENSE)
