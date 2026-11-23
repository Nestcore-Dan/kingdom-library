---
type: Guide
title: How to read this bundle
description: "For agents and people: layout, IDs, citations, trust and extension keys of this bundle."
generated: { by: kb/okf-mirror, at: "2026-11-20T00:00:00Z" }
---

# Reading this bundle

This folder is an [Open Knowledge Format](https://github.com/open-knowledge-format/open-knowledge-format) v0.3
bundle, kept in step with the knowledge base automatically. Don't edit it by hand - change things in the
knowledge base (web UI, REST API or MCP tools) and the mirror rewrites the files within a few seconds.

* Start at [index.md](index.md), then each folder's `index.md`. Every concept is one Markdown file with YAML
  frontmatter; its path (without `.md`) is its ID.
* `type` says what it is (Tool, LLM, Technique, Reference, ...). Knowledge that belongs to a product is filed
  under it, e.g. `tools/<tool>/<entry>.md`.
* Claims cite sources with footnotes such as `[^SRC-KB-0042]`; the label is the `id` of an entry in the
  concept's `sources`, which points at `references/SRC-KB-0042.md`.
* Trust: `generated` says who wrote the content, `verified` who confirmed it. Only a `human:` verification at
  or after `generated.at` makes a concept human-reviewed. Most content is machine-written and unverified.
* `status: deprecated` with `superseded_by` means the concept moved or was merged - follow the link.
* Keys starting with `x-kb-` are this library's own: `x-kb-reputability` is the owner's rating of a source
  (house rules R4), which OKF itself does not store.
