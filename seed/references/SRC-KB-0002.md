---
type: Reference
title: "Vibe-Automating a $6k Workflow in Less than 20 Minutes"
description: "This video demonstrates how to build a computer-use agent using Orgo, Cursor, and Claude to automate data extraction from a product website (SanMar) and populate it into a Google Sheet."
resource: "https://www.youtube.com/watch?v=gHCZzYBZy4U"
tags: [Agent frameworks, "Browser & computer use", Coding agents, Prompting]
status: stable
sources:
  - { id: SRC-KB-0002, resource: "https://www.youtube.com/watch?v=gHCZzYBZy4U", title: "Vibe-Automating a $6k Workflow in Less than 20 Minutes", author: "youtube:Nick-Vasilescu", last_modified: "2025-11-21" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0002
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 1041.0
---

This video demonstrates how to build a computer-use agent using Orgo, Cursor, and Claude to automate data extraction from a product website (SanMar) and populate it into a Google Sheet. The agent navigates web pages, extracts structured data, and switches contexts to input data without requiring API integrations or manual login. The process is shown to take under 20 minutes and is framed as a scalable, low-code automation solution for clients willing to pay $6k for such a service.

# Core method

Set up a new Orgo workspace and computer; configure a Cursor-based agent with Claude 4.5 Sonnet to navigate a target website, extract product details (SKU, color, price, description), and auto-populate them into a Google Sheet. Pre-configure the agent to open necessary browser tabs and avoid manual logins. Test and run the agent to complete the workflow.

# Key takeaways

* Use Orgo to create a computer-use agent environment without needing API keys or backend code.
* Configure the agent via Cursor to use Claude 4.5 Sonnet for navigation and data extraction.
* Automate data entry into Google Sheets by switching tabs and inputting structured data.
* Pre-configure browser tabs (Google Sheets and target site) to avoid repeated logins or navigation.
* The agent can be set to remain running for repeated use, with optional termination to save costs.
* The workflow can be shared via a public Google Sheet link for collaborative editing.

# Insights

* Pre-configure browser tabs to avoid repeated logins or navigation. _(principle; unreviewed, unknown confidence; about Browser & computer use)_
* Use AI agents to automate workflows without requiring API integrations or backend code. _(principle; unreviewed, unknown confidence; about Browser & computer use, Low-code automation)_
* [4:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=270s) Use AI agents to switch contexts and input data without manual intervention. _(principle; unreviewed, unknown confidence; about Browser & computer use)_
* [12:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=720s) Set up agents to remain running for repeated use, with optional termination to save costs. _(principle; unreviewed, unknown confidence; about Browser & computer use)_
* [13:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=810s) Use AI agents to extract structured data from web pages and populate it into Google Sheets. _(principle; unreviewed, unknown confidence; about Browser & computer use, Google Sheets integration)_
* [7:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=450s) Use the 'Share' button in Google Sheets to share the document with clients or collaborators. _(tip; unreviewed, unknown confidence; about Google Sheets)_
* [10:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=630s) Configure the agent to open necessary browser tabs (Google Sheets and target site) to avoid repeated logins or navigation. _(tip; unreviewed, unknown confidence; about GrokBot)_
* [10:30](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=630s) Use the 'claude-sonnet-4-5' model in the agent configuration for navigation and data extraction. _(tip; unreviewed, unknown confidence; about Claude)_
* [12:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=720s) Set up the agent to remain running for repeated use, with optional termination to save costs. _(tip; unreviewed, unknown confidence; about GrokBot)_
* [12:00](https://www.youtube.com/watch?v=gHCZzYBZy4U&t=720s) Use the 'Hey. What do you want to automate?' prompt in the agent interface to initiate automation tasks. _(tip; unreviewed, unknown confidence; about GrokBot)_

# Covers

* [SanMar](../companies/sanmar.md) - company, core
* [Anthropic](../companies/anthropic.md) - company, core
* [Browser & computer use](../concepts/browser-computer-use.md) - concept, core
* [Coding agents](../concepts/coding-agents.md) - concept, core
* [Agent orchestration](../concepts/agent-orchestration.md) - concept, core
* [Claude](../llms/cursor.md) - llm, core
* [Google Sheets](../tools/google-sheets.md) - tool, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [Firefox](../tools/firefox.md) - tool, core
* [Python](../tools/python.md) - tool, core
* [Computer Use](../tools/computer-use.md) - tool, core
* [Business & monetisation](../topics/business-monetisation.md) - topic, core
* [Automation & workflows](../topics/automation-workflows.md) - topic, core
* [Low-code automation](../topics/low-code-automation.md) - topic, core
* [Google Sheets integration](../topics/google-sheets-integration.md) - topic, core
* [Prompt Engineering](../topics/prompt-engineering.md) - topic, core
* [Port Authority Trace Heather Polo](../companies/sanmar/port-authority-trace-heather-polo.md) - concept, supporting
* [Gemini](../tools/gemini.md) - tool, supporting
* [computer_use_agent.py](../tools/computer-use-agent-py.md) - tool, supporting
* [pip](../tools/pip.md) - tool, supporting

# Our rating

Unassessed. KB house rules R4 - see the house rules.
