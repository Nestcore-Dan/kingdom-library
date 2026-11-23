---
type: LLM
title: Claude
description: An AI-powered code editor and agent platform that integrates with Claude to build and configure computer-use agents for automation tasks.
tags: [Agent frameworks, "Automation & workflows", "Browser & computer use", Coding agents, Evaluation, "MCP & tool use", Multi-agent, Prompting]
status: stable
sources:
  - { id: SRC-KB-0003, resource: "/references/SRC-KB-0003.md", title: How I Wish Someone Explained Computer Use Agents To Me }
  - { id: SRC-KB-0014, resource: "/references/SRC-KB-0014.md", title: My AI Swarm Reverse Engineered Higgsfield So You Don't Have To }
  - { id: SRC-KB-0002, resource: "/references/SRC-KB-0002.md", title: "Vibe-Automating a $6k Workflow in Less than 20 Minutes" }
  - { id: SRC-KB-0013, resource: "/references/SRC-KB-0013.md", title: I Stole the Best Part of Every AI Agent... With One Prompt (Open Source) }
  - { id: SRC-KB-0011, resource: "/references/SRC-KB-0011.md", title: "Are You Actually Behind on AI? | Corey Ganim & Spencer Kinney" }
  - { id: SRC-KB-0009, resource: "/references/SRC-KB-0009.md", title: "How He Sells AI Agents for €2,750 + Monthly Support" }
  - { id: SRC-KB-0001, resource: "/references/SRC-KB-0001.md", title: He Made AI Agents Work as a Team }
  - { id: SRC-KB-0008, resource: "/references/SRC-KB-0008.md", title: Your AI Agent Needs a Phone Number }
  - { id: SRC-KB-0007, resource: "/references/SRC-KB-0007.md", title: "Don’t Sell AI Agents for $5K/Month, Earn Equity Instead" }
  - { id: SRC-KB-0015, resource: "/references/SRC-KB-0015.md", title: Obsidian Tutorial for Beginners }
  - { id: SRC-KB-0005, resource: "/references/SRC-KB-0005.md", title: Sell AI Employees to Small Businesses (just steal mine) }
  - { id: SRC-KB-0004, resource: "/references/SRC-KB-0004.md", title: Make Money With a One-Person Agent Business - Here's How }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T16:52:29+11:00" }
x-kb-kind: llm
x-kb-slug: cursor
x-kb-origin: auto
x-kb-aliases: [anthropiccclaudeopus46, anthropicclaudeopus45, claude45sonnet, claude45sonnetllm, claudeagent, claudeagentactive, claudeanthropic, claudecode, claudecode21323, claudecodetool, claudedemo, claudedocs, claudedocstool, claudefable52, claudefable52high, claudefable52hightool, claudefable52llm, claudellm, claudeopus, claudeopus45, claudeopus46, claudeopus65, cursor, cursoraiagent, dessa, fable7, kemi, opus48, sonnet46, sonnet5]
x-kb-parent: "/concepts/coding-agents.md"
x-kb-relevance: core
---

[Prompt Engineering](../topics/prompt-engineering.md) › [Coding agents](../concepts/coding-agents.md) › Claude

An AI-powered code editor and agent platform that integrates with Claude to build and configure computer-use agents for automation tasks.

# Skills

* claude-handoff - Hand the current conversation off to a fresh background agent that picks up the work immediately.
* git-guardrails-claude-code - Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute.
* writing-for-agents - Writing documents for agents.

# Includes

[computer_use_agent.py](../tools/computer-use-agent-py.md), [Opus 5.5](claude-opus-5-5.md), [Opus 6.5](opus-6-5.md)

# Principles

* Claude Opus 4.5 is the current best model for computer-use tasks, hosted via Orgo.ai.[^SRC-KB-0003] _(unreviewed, unknown confidence)_ [1:30](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=90s)

# Tool-specific tips

* Use Claude Code to write, test, and deploy code for AI agents and software platforms.[^SRC-KB-0014] _(unreviewed, unknown confidence)_ [9:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=540s)
* Use the 'claude-sonnet-4-5' model in the agent configuration for navigation and data extraction.[^SRC-KB-0002] _(unreviewed, unknown confidence)_ [10:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=630s)

# Seen in

* [My AI Swarm Reverse Engineered Higgsfield So You Don't Have To](../references/SRC-KB-0014.md) (2026-11-14)
  * [1:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=90s) The AI agent framework used to spin up the computers for the swarm.
  * [3:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=180s) An AI agent used to perform tasks on the Orgo computers.
  * [7:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=450s) An AI agent that can interact with the T3 Code environment and execute commands.
  * [9:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=540s) An AI tool installed on the computer to facilitate agent tasks.
  * [10:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=630s) AI agent for computer use, used to replicate UI.
  * [10:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=630s) Specific version of Claude Code used for testing.
  * [12:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=720s) An AI model used for computer use and browser use tasks.
  * [16:30](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=990s) Used for code generation and editing.
  * [18:00](https://www.youtube.com/watch?v=OEqm3w_7ACg&t=1080s) Used to reverse engineer the Higgsfield platform and generate the cloned application.
* [I Stole the Best Part of Every AI Agent... With One Prompt (Open Source)](../references/SRC-KB-0013.md) (2026-11-11)
  * [15:00](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=900s) Selected as the primary model for the project with 'Medium' reasoning.
  * [25:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=1530s) The AI model selected and used for generating code and responses.
  * [25:30](https://www.youtube.com/watch?v=ceU0tS6sXbU&t=1530s) A large language model mentioned for potential integration.
* [Are You Actually Behind on AI? | Corey Ganim & Spencer Kinney](../references/SRC-KB-0011.md) (2026-10-27)
  * [1:30](https://www.youtube.com/watch?v=oumG87tIggg&t=90s) Mentioned as a free AI tool used by the general public.
  * [3:00](https://www.youtube.com/watch?v=oumG87tIggg&t=180s) Cited as a future model that will be even better.
  * [4:30](https://www.youtube.com/watch?v=oumG87tIggg&t=270s) A new voice model released by Brick, described as a 'voice-to-voice' model that sounds like a human.
  * [4:30](https://www.youtube.com/watch?v=oumG87tIggg&t=270s) A large language model mentioned as a benchmark for comparison with the new Kemi model.
  * [4:30](https://www.youtube.com/watch?v=oumG87tIggg&t=270s) A new model mentioned as having comparable performance to Claude Opus but at half the cost.
* [How He Sells AI Agents for €2,750 + Monthly Support](../references/SRC-KB-0009.md) (2026-10-01)
  * [4:30](https://www.youtube.com/watch?v=Y8MJG3iDtSo&t=270s) General-purpose LLM mentioned as being outperformed by the AI agent.
  * [6:00](https://www.youtube.com/watch?v=Y8MJG3iDtSo&t=360s) An AI model mentioned as a competitor that does not retain memory like Honcho.
  * [9:00](https://www.youtube.com/watch?v=Y8MJG3iDtSo&t=540s) A large language model used by clients for various tasks, mentioned as a competitor.
  * [22:30](https://www.youtube.com/watch?v=Y8MJG3iDtSo&t=1350s) Mentioned as a familiar interface that some customers use.
  * [24:00](https://www.youtube.com/watch?v=Y8MJG3iDtSo&t=1440s) An LLM mentioned as a topic of content creation, not directly related to the agent sales discussion.
* [He Made AI Agents Work as a Team](../references/SRC-KB-0001.md) (2026-09-25)
  * [0:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=0s) An AI agent mentioned as one of the tools users are trying to orchestrate.
  * [1:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=90s) Mentioned as an LLM with specific strengths.
  * [9:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=540s) An AI model used within the Tango platform for generating task breakdowns.
  * [10:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=630s) An AI agent type shown as 'claude agent active' in the agent list.
  * [15:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=900s) An AI agent within Tango, scoped to 'TangoTest' for tasks like agent code writing.
  * [16:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=990s) An AI model used as an agent within the Tango platform, shown with its connection and scope details.
  * [18:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1080s) An AI model used as an example for managing tasks through Tango.
  * [19:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1170s) An AI agent mentioned as an example of an assignee in the Tango system.
* [Your AI Agent Needs a Phone Number](../references/SRC-KB-0008.md) (2026-09-14)
  * [15:00](https://www.youtube.com/watch?v=DlILpW2FRNE&t=900s) Mentioned as an LLM that could build general agent platforms.
  * [16:30](https://www.youtube.com/watch?v=DlILpW2FRNE&t=990s) An LLM mentioned as an example of a large model that won't build tools for niche industries like real estate.
* [Don’t Sell AI Agents for $5K/Month, Earn Equity Instead](../references/SRC-KB-0007.md) (2026-09-04)
  * [22:30](https://www.youtube.com/watch?v=pjvT25T_81o&t=1350s) An AI tool that can be integrated with Seedly CRM to customize its functionality.
* [Obsidian Tutorial for Beginners](../references/SRC-KB-0015.md) (2026-07-29)
  * [0:00](https://www.youtube.com/watch?v=lsytBlAdJK4&t=0s) An AI tool connected to Obsidian for searching, summarizing, and building on notes.
  * [9:00](https://www.youtube.com/watch?v=lsytBlAdJK4&t=540s) An AI assistant tool that can access and process Obsidian notes.
  * [9:00](https://www.youtube.com/watch?v=lsytBlAdJK4&t=540s) An AI model used within the Claude app.
  * [10:30](https://www.youtube.com/watch?v=lsytBlAdJK4&t=630s) An AI model used to search the user's vault, create notes, and summarize feedback.
* [Sell AI Employees to Small Businesses (just steal mine)](../references/SRC-KB-0005.md) (2026-07-02)
  * [4:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=270s) A tool listed in the Hermes Agent's available tools.
  * [15:00](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=900s) An AI agent used to provide instructions for setting up the Telegram bot.
  * [18:00](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1080s) An agent used to install the 'Orgo computer skill'.
  * [31:30](https://www.youtube.com/watch?v=fAhwYrjmQRk&t=1890s) An AI agent tool used to set up and manage agents.
* [Make Money With a One-Person Agent Business - Here's How](../references/SRC-KB-0004.md) (2026-06-13)
  * [0:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=0s) Mentioned as an example of an AI agent platform.
  * [4:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=270s) An AI model used in job postings.
  * [6:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=360s) AI model mentioned in job postings.
  * [13:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=810s) A code history tool connected to the Hermes Agent via Obsidian.
  * [15:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=900s) An LLM model used by the Hermes Agent, shown running in the terminal.
  * [15:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=900s) Anthropic's terminal coding agent, shown as a competing template.
  * [16:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=990s) An LLM model mentioned in the terminal output.
  * [18:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1080s) A specific model selected for use with the Hermes Agent.
  * [19:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1170s) An LLM mentioned by the presenter as a benchmark for Kimmy 2.7.
  * [21:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1260s) An AI coding agent that can be connected to Ideabrowser and used within Hermes Agent.
  * [22:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1350s) An AI coding tool used by the agent, as indicated by the 'skill' line in the terminal output.
  * [24:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1440s) An AI code assistant being installed via the agent.
  * [27:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=1620s) An alternative AI agent mentioned but not used in this demonstration.
  * [36:00](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=2160s) A tool or model referenced in the interface, likely for AI-related tasks.
  * [37:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=2250s) An AI model mentioned in the interface, likely used by the Hermes Agent.
  * [40:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=2430s) An AI model (Claude Cowork and Claude Code) available for installation via Composio.
  * [43:30](https://www.youtube.com/watch?v=kdvm_kRZk8A&t=2610s) Not explicitly shown but mentioned in the context of agent tools.
* [How I Wish Someone Explained Computer Use Agents To Me](../references/SRC-KB-0003.md) (2025-12-06)
  * [0:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=0s) An AI model used as an example for 'Computer Using Models'.
  * [1:30](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=90s) The best current computer use model mentioned.
  * [1:30](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=90s) IDE used to view the orchestrator.py file.
  * [4:30](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=270s) An AI model used within the ESP Auto-CUA interface to generate commands and suggestions.
  * [6:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=360s) An AI agent mentioned as an example of an LLM agent.
  * [7:30](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=450s) An integrated development environment (IDE) used to run the Python script.
  * [9:00](https://www.youtube.com/watch?v=t6wWLVd-C_I&t=540s) An IDE used to view and run the Python automation script.
* [Vibe-Automating a $6k Workflow in Less than 20 Minutes](../references/SRC-KB-0002.md) (2025-11-21)
  * [0:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=0s) AI model mentioned as the agent's core, though not directly shown in screenshots.
  * [3:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=180s) IDE used to open a project.
  * [3:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=180s) Documentation site for Claude's computer use tool, referenced for context.
  * [6:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=360s) Used to create and control an AI agent to automate web navigation and data entry.
  * [7:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=450s) An AI agent development platform used to plan and execute automation tasks.
  * [9:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=540s) The specific AI model used by the agent for task planning and execution.
  * [9:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=540s) A code editor used to write and manage the agent's code.
  * [10:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=630s) Code editor used for editing the README.md file.
  * [10:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=630s) AI agent used to automate the workflow.
  * [12:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=720s) The AI model used by the agent to perform the task.
  * [13:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=810s) AI agent used to automate the web navigation and data entry tasks.
  * [16:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=990s) Used as computer use agent to automate data entry.

# Related

[GrokBot](../tools/cloud-desktop.md), [AI agents](../concepts/agent.md), [Anthropic](../companies/anthropic.md), [Cloud Computing](../topics/cloud-computing.md), [AgentMail](../tools/agentmail.md), [Prompt Engineering](../topics/prompt-engineering.md), [Composio](../tools/composio.md), [Telegram](../services/telegram.md), [OpenAI](../companies/openai.md), [Obsidian](../tools/obsidian.md), [n8n](../tools/n8n.md), [Coding agents](../concepts/coding-agents.md), [Model Context Protocol (MCP)](../concepts/model-context-protocol-mcp.md), [iMessage/RCS](../services/imessage-rcs.md), [Nick Vasilescu](../people/nick-vasilescu.md)

[^SRC-KB-0003]: [How I Wish Someone Explained Computer Use Agents To Me](../references/SRC-KB-0003.md)
[^SRC-KB-0014]: [My AI Swarm Reverse Engineered Higgsfield So You Don't Have To](../references/SRC-KB-0014.md)
[^SRC-KB-0002]: [Vibe-Automating a $6k Workflow in Less than 20 Minutes](../references/SRC-KB-0002.md)
