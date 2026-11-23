---
type: Dataset
title: Multimodal Knowledge Agent
description: "A benchmark dataset for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains."
tags: [Evaluation]
status: stable
sources:
  - { id: SRC-KB-0020, resource: "/references/SRC-KB-0020.md", title: google/multimodal-knowledge-agent }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T19:43:26+11:00" }
x-kb-kind: dataset
x-kb-slug: multimodal-knowledge-agent
x-kb-origin: auto
x-kb-parent: "/companies/google-deepmind.md"
x-kb-relevance: core
---

[Google DeepMind](../companies/google-deepmind.md) › Multimodal Knowledge Agent

A benchmark dataset for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains.

# Principles

* Multimodal Knowledge Agent (MKA) is a benchmark from Google DeepMind for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains.[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* Unlike text-extractable benchmarks where attachments can be solved via plain-text extraction or OCR alone, every MKA task contains a multi-file workspace with load-bearing visual artifacts...[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* Every MKA task contains a multi-file workspace with load-bearing visual artifacts—such as architectural CAD blueprints, electrical and RF schematics, geospatial rasters, seasonal dependency graphs, biochemical gel and spectrophotometric plates, and multi-axis charts...[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* MKA requires native multimodal perception, cross-document synthesis, tool orchestration (code execution, file inspection), and standalone deliverable generation (`.xlsx`, `.pptx`, `.docx`, `.json`, or structured technical reports).[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* Each `metadata.json` contains: TaskID, Prompt, All Task Files, Rubric Criteria, Input_files, Vertical, Domain, Role, Task Goal, Economic Rationale.[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* The dataset includes 10 unique domains and verticals: Logistics & Mapping, Construction, Engineering, Science, Business, Finance, Education, Law & Government, Software & Data.[^SRC-KB-0020] _(unreviewed, high confidence, observation)_
* Tasks are designed to require real-world professional time and value context, as captured in the 'Economic Rationale' field.[^SRC-KB-0020] _(unreviewed, high confidence, observation)_

# Seen in

* [google/multimodal-knowledge-agent](../references/SRC-KB-0020.md) (2026-11-10)

# Related

[Google DeepMind](../companies/google-deepmind.md)

[^SRC-KB-0020]: [google/multimodal-knowledge-agent](../references/SRC-KB-0020.md)
