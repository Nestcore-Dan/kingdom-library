---
type: Reference
title: I Stole the Best Part of Every AI Agent... With One Prompt (Open Source)
description: "Nick Vasilescu demonstrates how to prompt Claude Fable 5.2 High to synthesize features from multiple AI agent platforms (Grok Bot, Muse, Dots, Hermes, Instinct, Duet) into a single open-source agent platform hosted on a live URL using T3…"
resource: "https://www.youtube.com/watch?v=ceU0tS6sXbU"
tags: [Agent frameworks, Coding agents, "Infrastructure & hosting", "MCP & tool use", Multi-agent, Prompting]
status: stable
sources:
  - { id: SRC-KB-0013, resource: "https://www.youtube.com/watch?v=ceU0tS6sXbU", title: I Stole the Best Part of Every AI Agent... With One Prompt (Open Source), author: "youtube:Nick-Vasilescu", last_modified: "2026-11-11" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0013
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 2186.0
---

Nick Vasilescu demonstrates how to prompt Claude Fable 5.2 High to synthesize features from multiple AI agent platforms (Grok Bot, Muse, Dots, Hermes, Instinct, Duet) into a single open-source agent platform hosted on a live URL using T3 Code and Orgo computers. The process involves sourcing open-source repos and APIs for each component, then instructing the agent to assemble them into a cohesive system with UI, voice, social, and computer control capabilities. The result is a working agent platform built in under three hours using one prompt.

# Core method

Identify the best feature from each AI agent platform you want to combine. Find the open-source repo, API, or MCP that implements that feature. Draft a detailed prompt in T3 Code specifying the desired architecture, tools, and integrations. Send the prompt to a high-capacity coding agent (e.g., Claude Fable 5.2 High) and let it build the system autonomously. Host and test the result on a cloud computer (e.g., Orgo) using the agent’s built-in harness (e.g., Hermes).

# Key takeaways

* You can build a custom AI agent platform by prompting a coding agent to assemble existing open-source components.
* T3 Code and Orgo provide cloud-based environments to run and test agent projects with multiple machines.
* Hermes Agent serves as a model-agnostic harness that can integrate any LLM and connect to existing APIs and tools.
* The agent can generate a live web interface, manage multiple bots, and control remote computers via screen-sharing.
* Features like iMessage, voice, social media, and computer UI can be replicated using existing open-source repos and MCPs.
* The entire platform can be built from scratch using one prompt and a coding agent, with no prior coding required.

# Insights

* You can build a custom AI agent platform by prompting a coding agent to assemble existing open-source components. _(principle; unreviewed, unknown confidence; about Agent architecture, Prompt Engineering, Open-Source, Coding agents)_
* [4:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=270s) Features like iMessage, voice, social media, and computer UI can be replicated using existing open-source repos and MCPs. _(principle; unreviewed, unknown confidence; about Coding agents)_
* [9:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=540s) The agent can generate a live web interface, manage multiple bots, and control remote computers via screen-sharing. _(principle; unreviewed, unknown confidence; about Browser & computer use)_
* [10:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=630s) Hermes Agent serves as a model-agnostic harness that can integrate any LLM and connect to existing APIs and tools. _(principle; unreviewed, unknown confidence; about Coding agents)_
* [13:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=810s) T3 Code and Orgo provide cloud-based environments to run and test agent projects with multiple machines. _(principle; unreviewed, unknown confidence; about Cloud Computing)_
* [15:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=900s) The entire platform can be built from scratch using one prompt and a coding agent, with no prior coding required. _(principle; unreviewed, unknown confidence; about Prompt Engineering, Coding agents)_
* [3:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=180s) Use Figma to design and visualize the UI/UX of the agent platform. _(tip; unreviewed, unknown confidence; about Figma)_
* [10:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=630s) Use Hermes Agent to integrate any LLM and connect to existing APIs and tools. _(tip; unreviewed, unknown confidence; about AI agents)_
* [13:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=810s) Use Orgo to host and test the agent platform on a cloud computer using the agent’s built-in harness. _(tip; unreviewed, unknown confidence; about GrokBot)_
* [18:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=1080s) Use Composio to connect AI agents to APIs and services via MCP. _(tip; unreviewed, unknown confidence; about Composio)_
* [19:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=1170s) Use GitHub to source open-source repos and APIs for each component. _(tip; unreviewed, unknown confidence; about GitHub)_
* [21:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=1260s) Use T3 Code to draft a detailed prompt specifying the desired architecture, tools, and integrations. _(tip; unreviewed, unknown confidence; about Treg)_

# Covers

* [Anthropic](../companies/anthropic.md) - company, core
* [OpenAI](../companies/openai.md) - company, core
* [AI agents](../concepts/agent.md) - concept, core
* [Browser & computer use](../concepts/browser-computer-use.md) - concept, core
* [Coding agents](../concepts/coding-agents.md) - concept, core
* [Agent architecture](../concepts/agent-architecture.md) - concept, core
* [Multi-agent systems](../concepts/multi-agent-systems.md) - concept, core
* [Opus 5.5](../llms/claude-opus-5-5.md) - llm, core
* [Claude](../llms/cursor.md) - llm, core
* [iMessage/RCS](../services/imessage-rcs.md) - service, core
* [X (formerly Twitter)](../services/x-formerly-twitter.md) - service, core
* [GitHub](../services/github.md) - service, core
* [Slack](../services/slack.md) - service, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [Figma](../tools/figma.md) - tool, core
* [Treg](../tools/t3-code.md) - tool, core
* [Composio](../tools/composio.md) - tool, core
* [Muse](../tools/muse.md) - tool, core
* [Dots](../tools/dots.md) - tool, core
* [n8n](../tools/n8n.md) - tool, core
* [OpenClaw](../tools/openclaw.md) - tool, core
* [AgentMail](../tools/agentmail.md) - tool, core
* [Honcho](../tools/honcho.md) - tool, core
* [Bops](../tools/bops.md) - tool, core
* [Paper MCP](../tools/paper.md) - tool, core
* [Duet](../tools/duet.md) - tool, core
* [Computer Use](../tools/computer-use.md) - tool, core
* [AgentPhone](../tools/agentphone-ai.md) - tool, core
* [Prompt Engineering](../topics/prompt-engineering.md) - topic, core
* [Cloud Computing](../topics/cloud-computing.md) - topic, core
* [Open-Source](../topics/open-source.md) - topic, core
* [xAI](../companies/xai.md) - company, supporting
* [Barbie](../tools/barbie.md) - tool, supporting
* [Linux](../tools/linux.md) - tool, supporting
* [Instinct](../tools/instinct.md) - tool, supporting

# Our rating

Unassessed. KB house rules R4 - see the house rules.
