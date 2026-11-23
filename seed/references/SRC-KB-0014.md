---
type: Reference
title: My AI Swarm Reverse Engineered Higgsfield So You Don't Have To
description: "Nick Vasilescu demonstrates how an AI agent swarm (15 Claude Code agents on Orgo cloud computers) reverse-engineered Higgsfield AI by mapping its UI and architecture into a spec, then rebuilt a functional open-source clone called Parallax."
resource: "https://www.youtube.com/watch?v=OEqm3w_7ACg"
tags: ["Browser & computer use", Coding agents, "MCP & tool use", Multi-agent, Prompting]
status: stable
sources:
  - { id: SRC-KB-0014, resource: "https://www.youtube.com/watch?v=OEqm3w_7ACg", title: My AI Swarm Reverse Engineered Higgsfield So You Don't Have To, author: "youtube:Nick-Vasilescu", last_modified: "2026-11-14" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0014
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 1358.0
---

Nick Vasilescu demonstrates how an AI agent swarm (15 Claude Code agents on Orgo cloud computers) reverse-engineered Higgsfield AI by mapping its UI and architecture into a spec, then rebuilt a functional open-source clone called Parallax. The process involved orchestrating agents to test features, generate specs, and build a UI in Paper MCP, all for under $32. The final product is a free, open-source alternative with full model support and a live demo hosted on a public URL.

# Core method

Orchestrate a swarm of AI agents (e.g., Claude Code) on cloud computers (e.g., Orgo) using a prompt to map and rebuild a target platform’s UI and architecture. Each agent tests a different component, logs findings into a shared spec, and uses tools like Paper MCP to reconstruct the interface. Deploy the rebuilt platform as a live web app using cloud hosting.

# Key takeaways

* An AI swarm can reverse-engineer complex platforms like Higgsfield by assigning agents to test individual features and generate a unified spec.
* The rebuilt platform, Parallax, is fully functional and open-source, supporting models like Veo 3.1 and Seedance 2.5.
* The entire process cost less than $32 and took less than a day to complete, including deployment.
* Agents used browser automation and UI cloning to reconstruct Higgsfield’s interface in Paper MCP.
* The project demonstrates that AI agents can autonomously build software from scratch using reverse-engineered specs.
* The final product is hosted on a public URL and can be run locally with no API keys (demo mode).

# Insights

* AI agents can autonomously reverse-engineer complex platforms by dividing tasks among multiple agents and using shared specifications. _(principle; unreviewed, unknown confidence; about AI Agent Swarm)_
* [1:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=90s) A unified specification can be generated from multiple agent findings and used to reconstruct a functional platform. _(principle; unreviewed, unknown confidence; about AI Agent Swarm)_
* [9:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=540s) Cloud computing and agent orchestration enable rapid, low-cost deployment of AI agents for software development. _(principle; unreviewed, unknown confidence; about Cloud Computing)_
* [13:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=810s) UI cloning and browser automation can be used to reconstruct the visual interface of a platform without direct access to its code. _(principle; unreviewed, unknown confidence; about AI Agent Swarm)_
* [18:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=1080s) Open-source deployment is possible with minimal cost and effort, enabling public access to reverse-engineered platforms. _(principle; unreviewed, unknown confidence; about Open-Source)_
* [3:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=180s) Use Orgo’s 'Templates' to launch pre-configured agent templates for reverse-engineering tasks. _(tip; unreviewed, unknown confidence; about GrokBot)_
* [4:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=270s) Use T3 Code to orchestrate multiple agents and manage their tasks through prompts and threads. _(tip; unreviewed, unknown confidence; about Treg)_
* [9:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=540s) Use Claude Code to write, test, and deploy code for AI agents and software platforms. _(tip; unreviewed, unknown confidence; about Claude)_
* [15:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=900s) Use Paper MCP to clone and reconstruct UI components from browser automation logs. _(tip; unreviewed, unknown confidence; about Paper MCP)_
* [16:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=990s) Use Fable 5.2 to coordinate agent tasks and manage the orchestration process. _(tip; unreviewed, unknown confidence; about Fable 5.2)_

# Covers

* [Anthropic](../companies/anthropic.md) - company, core
* [AI Agent Swarm](../concepts/ai-agent-swarm.md) - concept, core
* [Model Context Protocol (MCP)](../concepts/model-context-protocol-mcp.md) - concept, core
* [Claude](../llms/cursor.md) - llm, core
* [Veo 3.1](../llms/veo-3-1.md) - llm, core
* [Nick Vasilescu](../people/nick-vasilescu.md) - person, core
* [Higgsfield](../services/higgsfield.md) - service, core
* [Parallax](../services/parallax.md) - service, core
* [GitHub](../services/github.md) - service, core
* [Treg](../tools/t3-code.md) - tool, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [Paper MCP](../tools/paper.md) - tool, core
* [Seedance 2.5](../tools/seedance-2-5.md) - tool, core
* [Composio](../tools/composio.md) - tool, core
* [Browser Automation](../topics/browser-automation.md) - topic, core
* [Prompt Engineering](../topics/prompt-engineering.md) - topic, core
* [Cloud Computing](../topics/cloud-computing.md) - topic, core
* [Open-Source](../topics/open-source.md) - topic, core
* [Fable 5.2](../llms/fable-5-2.md) - llm, supporting
* [Linux](../tools/linux.md) - tool, supporting
* [Reverse Engineer Agent (REA)](../tools/reverse-engineer-agent-rea.md) - tool, supporting
* [DevTools Protocol](../tools/devtools-protocol.md) - tool, supporting
* [Supercomputer](../tools/supercomputer.md) - tool, supporting
* [hf_cookies_gz](../tools/hf-cookies-gz.md) - tool, supporting
* [PRODUCT_SPEC.md](../tools/product-spec-md.md) - tool, supporting
* [bot hq](../tools/bot-hq.md) - tool, supporting

# Our rating

Unassessed. KB house rules R4 - see the house rules.
