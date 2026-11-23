---
type: Concept
title: Agent orchestration
description: The process of coordinating multiple AI agents to perform tasks in sequence or parallel.
tags: [Agent frameworks, "MCP & tool use", Multi-agent]
status: stable
sources:
  - { id: SRC-KB-0010, resource: "/references/SRC-KB-0010.md", title: How I Built an AI Bot That Runs My Business }
  - { id: SRC-KB-0005, resource: "/references/SRC-KB-0005.md", title: Sell AI Employees to Small Businesses (just steal mine) }
  - { id: SRC-KB-0001, resource: "/references/SRC-KB-0001.md", title: He Made AI Agents Work as a Team }
  - { id: SRC-KB-0006, resource: "/references/SRC-KB-0006.md", title: Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This. }
  - { id: SRC-KB-0002, resource: "/references/SRC-KB-0002.md", title: "Vibe-Automating a $6k Workflow in Less than 20 Minutes" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T17:38:13+11:00" }
x-kb-kind: concept
x-kb-slug: agent-orchestration
x-kb-origin: auto
x-kb-aliases: [agentframeworks, agentframeworksframeworkssdksforbuildingagentslanggraphcrewaiagentssdk]
x-kb-relevance: core
---

The process of coordinating multiple AI agents to perform tasks in sequence or parallel.

# Includes

[Agent architecture](agent-architecture.md), [Agent observability](../topics/agent-observability.md), [Agent Operators](agent-operators.md), [AI agents](agent.md), [Browser & computer use](browser-computer-use.md), [Computer Use Agents (CUA)](computer-use-agents-cua.md), [Deterministic Workflow Pipeline](deterministic-workflow-pipeline.md), [LLM Agents](llm-agents.md), [MCP & tool use](../topics/mcp-tool-use.md), [Minimal Viable Agent (MVA)](minimal-viable-agent-mva.md), [Multi-agent](../topics/multi-agent.md), [Tool Integration](../topics/tool-integration.md)

# Principles

* Design your AI agent platform in Paper first, then build the backend using T3 Code with Claude Opus 5.5 for guidance.[^SRC-KB-0010] _(unreviewed, unknown confidence)_
* Use OpenAI’s Harness API and GPT-6.1 model to power agent logic and voice interaction.[^SRC-KB-0010] _(unreviewed, unknown confidence)_ [7:30](https://www.youtube.com/watch?v=GCuj1KCTXok&t=450s)
* Deploy and test agents with real user interactions across platforms.[^SRC-KB-0010] _(unreviewed, unknown confidence)_ [9:00](https://www.youtube.com/watch?v=GCuj1KCTXok&t=540s)
* Agent orchestration is achieved by defining a workflow of tools and connectors, then using a central agent (like Hermes Agent) to manage execution and context.[^SRC-KB-0005] _(unreviewed, unknown confidence)_

# Seen in

* [How I Built an AI Bot That Runs My Business](../references/SRC-KB-0010.md) (2026-10-12)
* [He Made AI Agents Work as a Team](../references/SRC-KB-0001.md) (2026-09-25)
* [Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This.](../references/SRC-KB-0006.md) (2026-07-10)
* [Sell AI Employees to Small Businesses (just steal mine)](../references/SRC-KB-0005.md) (2026-07-02)
* [Vibe-Automating a $6k Workflow in Less than 20 Minutes](../references/SRC-KB-0002.md) (2025-11-21)

# Related

[GrokBot](../tools/cloud-desktop.md), [Claude](../llms/cursor.md), [AI agents](agent.md), [Multi-agent](../topics/multi-agent.md), [Cloud-based agent deployment](../companies/infrastructure-hosting/cloud-based-agent-deployment.md), [AgentPhone](../tools/agentphone-ai.md), [AgentMail](../tools/agentmail.md), [MCP & tool use](../topics/mcp-tool-use.md), [Prompt Engineering](../topics/prompt-engineering.md), [Coding agents](coding-agents.md), [Browser & computer use](browser-computer-use.md), [Computer Use](../tools/computer-use.md), [Composio](../tools/composio.md), [Model Context Protocol (MCP)](model-context-protocol-mcp.md), [JEV](../tools/jev.md)

[^SRC-KB-0010]: [How I Built an AI Bot That Runs My Business](../references/SRC-KB-0010.md)
[^SRC-KB-0005]: [Sell AI Employees to Small Businesses (just steal mine)](../references/SRC-KB-0005.md)
