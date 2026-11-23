---
type: Concept
title: Computer Use Agents (CUA)
description: Agents that use LLMs to interact with computer environments through deterministic workflows.
tags: [Agent frameworks, "Browser & computer use", Evaluation, "MCP & tool use", Multi-agent]
status: stable
sources:
  - { id: SRC-KB-0003, resource: "/references/SRC-KB-0003.md", title: How I Wish Someone Explained Computer Use Agents To Me }
  - { id: SRC-KB-0006, resource: "/references/SRC-KB-0006.md", title: Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This. }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T16:55:29+11:00" }
x-kb-kind: concept
x-kb-slug: computer-use-agents-cua
x-kb-origin: auto
x-kb-aliases: [computeruseagents]
x-kb-parent: "/concepts/agent-orchestration.md"
x-kb-relevance: core
---

[Agent orchestration](agent-orchestration.md) › Computer Use Agents (CUA)

Agents that use LLMs to interact with computer environments through deterministic workflows.

# Principles

* Computer-use agents operate via deterministic workflows (e.g., Python scripts) rather than fluid, non-deterministic LLM agent behavior.[^SRC-KB-0003] _(unreviewed, unknown confidence)_
* Agents can automate real-world tasks like downloading PDFs, opening browsers, and uploading files to S3 using natural language prompts.[^SRC-KB-0003] _(unreviewed, unknown confidence)_ [3:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=180s)
* Agents can be chained together (e.g., 5 agents in a workflow) to automate complex business processes like generating Zoho Books quotes from presentations.[^SRC-KB-0003] _(unreviewed, unknown confidence)_ [6:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=360s)

# Seen in

* [Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This.](../references/SRC-KB-0006.md) (2026-07-10)
* [How I Wish Someone Explained Computer Use Agents To Me](../references/SRC-KB-0003.md) (2025-12-06)
  * [6:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=360s) Agents that can perform tasks on a computer using natural language instructions, as opposed to requiring code.

# Related

[Prompt Engineering](../topics/prompt-engineering.md), [Computer Use](../tools/computer-use.md), [AI agents](agent.md), [GrokBot](../tools/cloud-desktop.md), [Evaluation](../topics/evaluation.md), [Model benchmarking](../topics/model-benchmarking.md), [Minions](../services/minions.md), [Orion Desk](../services/orion-desk.md), [Lichess.org](../services/lichess-org.md), [LeeChess.org](../services/leechess-org.md), [Muse](../tools/muse.md), [DeepSeek V4 Flash](../llms/deepseek-v4-flash.md), [GLM 5.2](../llms/glm-5-2.md), [Fable 5](../llms/fable-5.md), [Terra](../llms/terra.md)

[^SRC-KB-0003]: [How I Wish Someone Explained Computer Use Agents To Me](../references/SRC-KB-0003.md)
