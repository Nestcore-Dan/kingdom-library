---
type: Reference
title: google/multimodal-knowledge-agent
description: "**Multimodal Knowledge Agent (MKA)** is a benchmark from Google DeepMind for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains."
resource: "https://huggingface.co/datasets/google/multimodal-knowledge-agent"
tags: [Datasets, Evaluation]
status: stable
sources:
  - { id: SRC-KB-0020, resource: "https://huggingface.co/datasets/google/multimodal-knowledge-agent", title: google/multimodal-knowledge-agent, author: "huggingface:google", last_modified: "2026-11-10" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0020
x-kb-kind: dataset
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: hubwatch
---

**Multimodal Knowledge Agent (MKA)** is a benchmark from Google DeepMind for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains.

# Insights

* Each `metadata.json` contains: TaskID, Prompt, All Task Files, Rubric Criteria, Input_files, Vertical, Domain, Role, Task Goal, Economic Rationale. _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* Every MKA task contains a multi-file workspace with load-bearing visual artifacts—such as architectural CAD blueprints, electrical and RF schematics, geospatial rasters, seasonal dependency graphs, biochemical gel and spectrophotometric plates, and multi-axis charts... _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* MKA requires native multimodal perception, cross-document synthesis, tool orchestration (code execution, file inspection), and standalone deliverable generation (`.xlsx`, `.pptx`, `.docx`, `.json`, or structured technical reports). _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* Multimodal Knowledge Agent (MKA) is a benchmark from Google DeepMind for evaluating autonomous AI agents on complex, multi-step, real-world visual knowledge work across professional domains. _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* Tasks are designed to require real-world professional time and value context, as captured in the 'Economic Rationale' field. _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* The dataset includes 10 unique domains and verticals: Logistics & Mapping, Construction, Engineering, Science, Business, Finance, Education, Law & Government, Software & Data. _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_
* Unlike text-extractable benchmarks where attachments can be solved via plain-text extraction or OCR alone, every MKA task contains a multi-file workspace with load-bearing visual artifacts... _(principle; unreviewed, high confidence, observation; about Multimodal Knowledge Agent)_

# Covers

* [Google DeepMind](../companies/google-deepmind.md) - company, core
* [Multimodal Knowledge Agent](../datasets/multimodal-knowledge-agent.md) - dataset, core

# Our rating

Excellent (assessed by model (draft)). KB house rules R4 - see the house rules.
