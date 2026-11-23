---
type: Reference
title: Sell AI Employees to Small Businesses (just steal mine)
description: "This video walks through the step-by-step setup of a multi-tool AI agent system using Orgo.ai, AgentMail, AgentPhone.ai, Composio, AgentCard, and Obsidian, with integration via Hermes Agent and Claude Code."
resource: "https://www.youtube.com/watch?v=fAhwYrjmQRk"
tags: [Agent frameworks, "MCP & tool use", "RAG & memory"]
status: stable
sources:
  - { id: SRC-KB-0005, resource: "https://www.youtube.com/watch?v=fAhwYrjmQRk", title: Sell AI Employees to Small Businesses (just steal mine), author: "youtube:Nick-Vasilescu", last_modified: "2026-07-02" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0005
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 1972.0
---

This video walks through the step-by-step setup of a multi-tool AI agent system using Orgo.ai, AgentMail, AgentPhone.ai, Composio, AgentCard, and Obsidian, with integration via Hermes Agent and Claude Code. The creator demonstrates how to provision a virtual computer, configure email, phone, Telegram, and app connectors, install a knowledge base, and set up observability tools like Latitude.so. The workflow is designed for small businesses to deploy AI agents as autonomous employees with real-world capabilities.

# Core method

Start by spinning up a virtual computer on Orgo.ai with a pre-configured Hermes Agent. Then, sequentially integrate email (AgentMail), phone (AgentPhone.ai), communication (Telegram via Composio), tools (Composio connectors), payment (AgentCard), knowledge (Obsidian), and observability (Latitude.so) using CLI commands and agent prompts. Use Lucidchart to visualize the architecture and reuse the template for future agents.

# Key takeaways

* Use Orgo.ai to spin up a virtual computer with a pre-installed Hermes Agent for agent orchestration.
* Integrate AgentMail for email, AgentPhone.ai for phone number, and Composio for app connectors (e.g., Gmail, GitHub, Twitter).
* Set up Telegram via a bot and QR code pairing, enabling messaging and SMS integration.
* Install Obsidian as a knowledge base and connect it to the Hermes Agent for context.
* Use Latitude.so for agent observability and failure monitoring, with configuration via CLI.
* Create a reusable template in Orgo.ai to deploy identical agent setups in the future.

# Insights

* Agent orchestration is achieved by defining a workflow of tools and connectors, then using a central agent (like Hermes Agent) to manage execution and context. _(principle; unreviewed, unknown confidence; about Agent orchestration, Tool Integration)_
* [4:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=270s) AI agents can be deployed on cloud platforms (like Orgo.ai) with pre-configured toolchains, enabling rapid setup for small businesses. _(principle; unreviewed, unknown confidence; about Cloud-based agent deployment)_
* [7:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=450s) Tool integration is achieved by using APIs and CLI commands to connect agents to services like email, phone, and apps. _(principle; unreviewed, unknown confidence; about Tool Integration, MCP & tool use)_
* [18:00](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1080s) Agent observability is critical for debugging and optimizing agent performance, and can be implemented using tools like Latitude.so. _(principle; unreviewed, unknown confidence; about Agent observability)_
* [25:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1530s) Knowledge bases (like Obsidian) can be integrated with agents to provide context and improve decision-making. _(principle; unreviewed, unknown confidence; about RAG & memory)_
* [10:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=630s) Configure AgentPhone.ai with a phone number and API key, then use the CLI to set up the agent with the Hermes Agent. _(tip; unreviewed, unknown confidence; about AgentPhone)_
* [16:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=990s) Pair Telegram bots with AI agents using a QR code, which is generated and displayed in the terminal. _(tip; unreviewed, unknown confidence; about Telegram)_
* [18:00](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1080s) Use the Composio CLI to install app connectors (e.g., Gmail, GitHub) and configure them for agent use. _(tip; unreviewed, unknown confidence; about Composio)_
* [19:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1170s) Use the '/resume' command in the Hermes Agent terminal to continue a previous session with the same agent state. _(tip; unreviewed, unknown confidence; about AI agents)_
* [22:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1350s) Install AgentCard via 'npm install -g agent-cards' and configure it with a skill.md file for payment integration. _(tip; unreviewed, unknown confidence; about AgentCard)_

# Covers

* [AI agents](../concepts/agent.md) - concept, core
* [Agent orchestration](../concepts/agent-orchestration.md) - concept, core
* [Cloud-based agent deployment](../companies/infrastructure-hosting/cloud-based-agent-deployment.md) - concept, core
* [GPT-5.5](../llms/gpt-5-5.md) - llm, core
* [Claude](../llms/cursor.md) - llm, core
* [Google Gemini 3.5 Flash](../llms/google-gemini-3-5-flash.md) - llm, core
* [Telegram](../services/telegram.md) - service, core
* [Composio](../tools/composio.md) - tool, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [Obsidian](../tools/obsidian.md) - tool, core
* [AgentMail](../tools/agentmail.md) - tool, core
* [AgentPhone](../tools/agentphone-ai.md) - tool, core
* [Latitude](../tools/latitude-so.md) - tool, core
* [AgentCard](../tools/agentcard.md) - tool, core
* [MCP & tool use](../topics/mcp-tool-use.md) - topic, core
* [Tool Integration](../topics/tool-integration.md) - topic, core
* [Agent observability](../topics/agent-observability.md) - topic, core
* [Knowledge base setup](../topics/knowledge-base-setup.md) - topic, core
* [RAG & memory](../topics/rag-memory.md) - topic, core
* [Multi-agent](../topics/multi-agent.md) - topic, core
* [Nous Portal](../services/nous-portal.md) - service, supporting
* [QR Code](../services/telegram/qr-code.md) - technique, supporting
* [Lucidchart](../tools/lucidchart.md) - tool, supporting
* [Terminal](../tools/terminal.md) - tool, supporting
* [npx](../tools/npx.md) - tool, supporting
* [npm](../tools/npm.md) - tool, supporting

# Our rating

Unassessed. KB house rules R4 - see the house rules.
