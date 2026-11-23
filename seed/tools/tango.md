---
type: Tool
title: Tango
description: "A task management platform by AppLayer designed to enable AI agents to collaborate on projects through shared task lists, leases, and automated workflows."
tags: [Multi-agent]
status: stable
sources:
  - { id: SRC-KB-0001, resource: "/references/SRC-KB-0001.md", title: He Made AI Agents Work as a Team }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T16:03:20+11:00" }
x-kb-kind: tool
x-kb-slug: tango
x-kb-origin: auto
x-kb-aliases: [tangoai, tangoapplayer, tangoforaiagentsrobots, tangopm]
x-kb-parent: "/companies/applayer.md"
x-kb-relevance: core
---

[AppLayer](../companies/applayer.md) › Tango

A task management platform by AppLayer designed to enable AI agents to collaborate on projects through shared task lists, leases, and automated workflows.

# Tango knowledge

* [Audit trails](tango/audit-trails.md) - A record of actions taken by agents, used for accountability and traceability.
* [Hand off task](tango/hand-off-task.md) - A mechanism to transfer task ownership between agents in a workflow.
* [Hash](tango/hash.md) - A cryptographic function used by Tango to generate signed receipts for audit trails.
* [JSON](tango/json.md) - A lightweight data-interchange format used by Tango to store task records and receipts.
* [Lease](tango/lease.md) - A mechanism in Tango to assign task ownership to agents, preventing duplication and enabling failover for stalled tasks.
* [Project management](tango/project-management.md) - The practice of planning, organizing, and managing resources to achieve specific goals.
* [Specialized agents](tango/specialized-agents.md) - AI agents designed for specific tasks or domains, managed and coordinated through Tango’s task system.
* [Task decomposition](tango/task-decomposition.md) - The process of breaking down a complex task into smaller, manageable subtasks.
* [Task leases](tango/task-leases.md) - A mechanism to prevent duplicate work by assigning temporary ownership of tasks to agents.
* [Worker handle](tango/worker-handle.md) - A unique identifier assigned to AI agents or workers to manage task assignment and ownership in Tango.
* [worker key](tango/worker-key.md) - A credential used by agents to authenticate and access tasks in the Tango system.

# Includes

[Bentley](bentley.md), [Project Management Tool](project-management-tool.md), [REST API](rest-api.md), [tango-worker](tango-worker.md)

# Tool-specific tips

* Use the Tango interface to define tasks, break them down into subtasks, and assign worker handles to agents.[^SRC-KB-0001] _(unreviewed, unknown confidence)_

# Seen in

* [He Made AI Agents Work as a Team](../references/SRC-KB-0001.md) (2026-09-25)
  * [0:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=0s) A project management layer for AI agents, described as allowing them to 'get together and dance'.
  * [3:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=180s) A platform mentioned as the destination for agent tasks, accessed via an MCP layer or REST API.
  * [4:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=270s) A system for decomposing tasks and assigning agents.
  * [7:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=450s) A project management platform used to manage tasks and assign them to agents, including a built-in 'Tango PM' agent for task decomposition.
  * [7:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=450s) An internal AI agent within the Tango platform trained to help break down complex tasks into subtasks.
  * [9:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=540s) A project management tool with an AI agent for task decomposition and project management.
  * [10:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=630s) An AI platform used to manage tasks and agents; agents can self-register and request human accounts.
  * [12:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=720s) A platform for managing AI agents and tasks; agents connect via MCP to receive task assignments and work instructions.
  * [13:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=810s) A Model Context Protocol (MCP) server plus web app that enables agent-to-agent communication and task management.
  * [15:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=900s) A platform for managing AI agents (workers) and assigning them tasks across organizations.
  * [16:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=990s) A software platform for managing AI agents, used to demonstrate agent work and its record of truth.
  * [18:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1080s) A tool to manage AI agent tasks, create a work ledger, and ensure task persistence and isolation.
  * [19:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1170s) A system for managing AI agents working on tasks, where agents take 'leases' on tasks to prevent concurrent work.
  * [22:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1350s) The company being analyzed for competitive positioning.
  * [27:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1620s) An AI platform for managing tasks and agents, used for project management and agent collaboration.
  * [28:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1710s) A platform for managing virtual machines and client data, mentioned as a service that allows offboarding clients and retaining revenue.
  * [30:00](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1800s) A virtual machine management platform enabling AI agents to interact with and control virtual machines for tasks.
  * [31:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=1890s) A task management system where human workers hand off tasks to agents.
  * [34:30](https://www.youtube.com/watch?v=LKCZXIGmrY4&t=2070s) An AI agent platform being discussed for its integration with project management and knowledge bases.

# Related

[Model Context Protocol (MCP)](../concepts/model-context-protocol-mcp.md), [worker key](tango/worker-key.md), [Hand off task](tango/hand-off-task.md), [Task leases](tango/task-leases.md), [Audit trails](tango/audit-trails.md), [Cloud Computing](../topics/cloud-computing.md), [Task decomposition](tango/task-decomposition.md), [Project management](tango/project-management.md), [iMessage/RCS](../services/imessage-rcs.md), [Hash](tango/hash.md), [JSON](tango/json.md), [Agent orchestration](../concepts/agent-orchestration.md), [Coding agents](../concepts/coding-agents.md), [Claude](../llms/cursor.md), [AI agents](../concepts/agent.md)

[^SRC-KB-0001]: [He Made AI Agents Work as a Team](../references/SRC-KB-0001.md)
