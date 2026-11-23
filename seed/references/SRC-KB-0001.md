---
type: Reference
title: He Made AI Agents Work as a Team
description: "The video demonstrates how Tango, a project management layer built by AppLayer, enables AI agents to collaborate on tasks with shared ownership, audit trails, and task decomposition."
resource: "https://www.youtube.com/watch?v=LKCZXIGmrY4"
tags: [Multi-agent]
status: stable
sources:
  - { id: SRC-KB-0001, resource: "https://www.youtube.com/watch?v=LKCZXIGmrY4", title: He Made AI Agents Work as a Team, author: "youtube:Nick-Vasilescu", last_modified: "2026-09-25" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0001
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 2184.0
---

The video demonstrates how Tango, a project management layer built by AppLayer, enables AI agents to collaborate on tasks with shared ownership, audit trails, and task decomposition. It shows how agents can be assigned worker identities, manage leases to avoid duplication, recover stalled tasks, and integrate with cloud desktops via Orgo. The system supports multi-agent workflows, task handoffs, and persistent task records for accountability and traceability.

# Core method

To implement agent teamwork using Tango, first define a task in a centralized project management interface. Break it down into subtasks using AI-assisted decomposition, assign worker handles to agents, and use task leases to prevent duplication. Enable automatic task polling via MCP or REST API, and use Orgo to provision cloud desktops when agents need physical compute. Maintain audit trails via signed receipts and JSON-based task records for transparency and accountability.

# Key takeaways

* Tango enables AI agents to collaborate on tasks with shared ownership, task decomposition, and audit trails.
* Agents can be assigned worker handles and automatically poll for tasks via MCP or REST API.
* Task leases prevent duplicate work, and stalled tasks can be recovered by other agents.
* Orgo provides cloud desktops that agents can drive to perform tasks requiring physical compute.
* Tango supports multi-agent workflows with handoff, delegation, and persistent task records.
* Agents can be configured to work autonomously, escalate tasks, or communicate via iMessage/RCS.

# Insights

* Agents can be configured to work autonomously, escalate tasks, or communicate via messaging services. _(principle; unreviewed, unknown confidence; about Specialized agents, iMessage/RCS)_
* Audit trails and signed receipts ensure accountability and traceability of agent actions. _(principle; unreviewed, unknown confidence; about Audit trails)_
* Cloud desktops and virtual machines enable agents to perform tasks requiring physical compute. _(principle; unreviewed, unknown confidence; about Cloud Computing, GrokBot)_
* Shared ownership and task decomposition enable multiple agents to collaborate on a single task. _(principle; unreviewed, unknown confidence; about Task decomposition)_
* Worker handles and task leases prevent duplication and ensure task ownership is managed. _(principle; unreviewed, unknown confidence; about Worker handle, Task leases)_
* Configure agents to poll for tasks via MCP or REST API to enable automatic task assignment. _(tip; unreviewed, unknown confidence; about Model Context Protocol (MCP))_
* Enable task leases to prevent duplicate work and ensure task ownership is managed. _(tip; unreviewed, unknown confidence; about Task leases)_
* Use JSON-based task records and signed receipts to maintain audit trails and ensure accountability. _(tip; unreviewed, unknown confidence; about JSON)_
* Use Orgo to provision cloud desktops for agents that need physical compute to perform tasks. _(tip; unreviewed, unknown confidence; about GrokBot)_
* Use the Tango interface to define tasks, break them down into subtasks, and assign worker handles to agents. _(tip; unreviewed, unknown confidence; about Tango)_

# Covers

* [AppLayer](../companies/applayer.md) - company, core
* [AI agents](../concepts/agent.md) - concept, core
* [Model Context Protocol (MCP)](../concepts/model-context-protocol-mcp.md) - concept, core
* [Coding agents](../concepts/coding-agents.md) - concept, core
* [Worker handle](../tools/tango/worker-handle.md) - concept, core
* [Specialized agents](../tools/tango/specialized-agents.md) - concept, core
* [Agent orchestration](../concepts/agent-orchestration.md) - concept, core
* [JSON](../tools/tango/json.md) - concept, core
* [Hash](../tools/tango/hash.md) - concept, core
* [Task leases](../tools/tango/task-leases.md) - concept, core
* [Hand off task](../tools/tango/hand-off-task.md) - concept, core
* [worker key](../tools/tango/worker-key.md) - concept, core
* [Claude](../llms/cursor.md) - llm, core
* [deepseek/deepseek-v4-pro](../llms/deepseek-deepseek-v4-pro.md) - llm, core
* [iMessage/RCS](../services/imessage-rcs.md) - service, core
* [Task decomposition](../tools/tango/task-decomposition.md) - technique, core
* [Tango](../tools/tango.md) - tool, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [REST API](../tools/rest-api.md) - tool, core
* [tango-worker](../tools/tango-worker.md) - tool, core
* [Project management](../tools/tango/project-management.md) - topic, core
* [Cloud Computing](../topics/cloud-computing.md) - topic, core
* [Audit trails](../tools/tango/audit-trails.md) - topic, core
* [Bentley](../tools/bentley.md) - tool, supporting

# Our rating

Unassessed. KB house rules R4 - see the house rules.
