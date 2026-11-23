---
type: Reference
title: Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This.
description: "The video demonstrates a head-to-head benchmark of multiple AI models (including Grok 4.5, GPT-5.6 Sol, Terra, Fable 5, and others) running concurrently as autonomous agents within the Orgo.ai platform, tasked with real-world computer use…"
resource: "https://www.youtube.com/watch?v=BFRmOxT8QIo"
tags: [Agent frameworks, "Browser & computer use", Evaluation, "MCP & tool use", Multi-agent]
status: stable
sources:
  - { id: SRC-KB-0006, resource: "https://www.youtube.com/watch?v=BFRmOxT8QIo", title: Grok 4.5 Blew Me Away. Then GPT-5.6 Sol Did This., author: "youtube:Nick-Vasilescu", last_modified: "2026-07-10" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0006
x-kb-kind: video
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: ytdl
x-kb-duration: 2612.0
---

The video demonstrates a head-to-head benchmark of multiple AI models (including Grok 4.5, GPT-5.6 Sol, Terra, Fable 5, and others) running concurrently as autonomous agents within the Orgo.ai platform, tasked with real-world computer use tasks like building websites, playing games, and interacting with web services. The presenter evaluates their speed, creativity, and reliability, concluding that GPT-5.6 Sol and Terra perform best in practical tasks, while Grok 4.5 impresses with persistence and creativity despite slower execution. The test environment uses Hermes Agent as a runtime interface for each model.

# Core method

Spin up multiple AI agents using a unified orchestration platform (Orgo.ai), assign each a different model, and simultaneously issue identical prompts for real-world tasks (e.g., building a website, playing chess, generating games). Monitor and compare completion times, output quality, and system stability across all agents to evaluate relative performance.

# Key takeaways

* GPT-5.6 Sol and Terra outperformed others in speed and practical task execution, including chess and website building.
* Grok 4.5 demonstrated strong creativity and persistence, often completing tasks but slower than top performers.
* Fable 5 and GLM 5.2 were underwhelming in practical tasks despite high cost or design capability.
* DeepSeek V4 Flash and Muse Spark 1.1 showed erratic or unstable behavior in real-time computer use.
* The Hermes Agent runtime enabled consistent model deployment and task execution across different platforms.

# Insights

* Real-world performance of AI agents depends not just on model capability, but on the orchestration platform, runtime, and task-specific prompting. _(principle; unreviewed, unknown confidence; about Computer Use, Multi-agent, Prompt Engineering)_
* [4:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=270s) Consistent deployment and standardized interfaces (like Hermes Agent) enable fair and repeatable benchmarking across different models. _(principle; unreviewed, unknown confidence; about AI agents, GrokBot, Model benchmarking)_
* [13:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=810s) Speed and reliability in real-world tasks are more important than creativity or persistence when the goal is task completion. _(principle; unreviewed, unknown confidence; about GPT-5.6 Sol, Terra, Computer Use)_
* [22:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=1350s) Model-specific strengths (e.g., Grok 4.5’s creativity) can be valuable but may not translate to practical task performance without optimized prompting or orchestration. _(principle; unreviewed, unknown confidence; about GrokBot, Prompt Engineering, Computer Use)_
* [25:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=1530s) Unstable or erratic behavior (e.g., DeepSeek V4 Flash) can undermine agent reliability, even if the model appears capable on paper. _(principle; unreviewed, unknown confidence; about DeepSeek V4 Flash, Evaluation, Multi-agent)_
* [3:00](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=180s) Configure Hermes Agent with specific model settings and reasoning effort to control agent behavior and performance. _(tip; unreviewed, unknown confidence; about AI agents)_
* [4:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=270s) Use Orgo.ai’s Minions workspace to spin up multiple agents with different models simultaneously for benchmarking. _(tip; unreviewed, unknown confidence; about GrokBot)_
* [15:00](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=900s) Use Orion Desk to provide each agent with a dedicated virtual desktop for consistent task execution. _(tip; unreviewed, unknown confidence; about Orion Desk)_
* [19:30](https://www.youtube.com/watch?v=BFRmOxT8QIo&t=1170s) Use Lichess.org or LeeChess.org to test AI agents’ real-time decision-making and game-playing capabilities. _(tip; unreviewed, unknown confidence; about Lichess.org)_

# Covers

* [AI agents](../concepts/agent.md) - concept, core
* [Agent orchestration](../concepts/agent-orchestration.md) - concept, core
* [Browser & computer use](../concepts/browser-computer-use.md) - concept, core
* [Computer Use Agents (CUA)](../concepts/computer-use-agents-cua.md) - concept, core
* [GPT-5.6 Sol](../llms/gpt-5-6-sol.md) - llm, core
* [Fable 5](../llms/fable-5.md) - llm, core
* [GLM 5.2](../llms/glm-5-2.md) - llm, core
* [DeepSeek V4 Flash](../llms/deepseek-v4-flash.md) - llm, core
* [Terra](../llms/terra.md) - llm, core
* [Orion Desk](../services/orion-desk.md) - service, core
* [Lichess.org](../services/lichess-org.md) - service, core
* [Minions](../services/minions.md) - service, core
* [LeeChess.org](../services/leechess-org.md) - service, core
* [GrokBot](../tools/cloud-desktop.md) - tool, core
* [Muse](../tools/muse.md) - tool, core
* [Computer Use](../tools/computer-use.md) - tool, core
* [Prompt Engineering](../topics/prompt-engineering.md) - topic, core
* [MCP & tool use](../topics/mcp-tool-use.md) - topic, core
* [Multi-agent](../topics/multi-agent.md) - topic, core
* [Model benchmarking](../topics/model-benchmarking.md) - topic, core
* [Evaluation](../topics/evaluation.md) - topic, core

# Our rating

Unassessed. KB house rules R4 - see the house rules.
