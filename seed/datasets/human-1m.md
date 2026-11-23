---
type: Dataset
title: Human-1M
description: "The largest and most diverse high-quality egocentric dataset for physical AI, containing 1M hours of human demonstrations."
tags: [Datasets, Vision]
status: stable
sources:
  - { id: SRC-KB-0021, resource: "/references/SRC-KB-0021.md", title: nvidia/PhysicalAI-Human-1M-100K }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T19:44:02+11:00" }
x-kb-kind: dataset
x-kb-slug: human-1m
x-kb-origin: auto
x-kb-parent: "/datasets/physicalai-human-1m-100k.md"
x-kb-relevance: core
---

[NVIDIA](../companies/nvidia.md) › [PhysicalAI-Human-1M-100K](physicalai-human-1m-100k.md) › Human-1M

The largest and most diverse high-quality egocentric dataset for physical AI, containing 1M hours of human demonstrations.

# Human-1M knowledge

* [Quality Gates](human-1m/quality-gates.md) - A set of automated and human-reviewed checks ensuring high-quality annotations, tasks, diversity, and 3D tracking.
* [T1](human-1m/t1.md) - A high-level task description in Human-1M, summarizing the overall goal, major actions, and key objects.
* [T2](human-1m/t2.md) - A timed subtask annotation in Human-1M, specifying 1–10-second segments with precise verbs and objects.
* [Task Clusters](human-1m/task-clusters.md) - Groupings of similar tasks within the Human-1M dataset, used to organize and analyze human work.

# Principles

* High-quality human demonstrations are essential for training physical AI models.[^SRC-KB-0021] _(unreviewed, high confidence, observation)_
* Episodes are the atomic unit of Human-1M, with strict requirements for video, motion, and language alignment.[^SRC-KB-0021] _(unreviewed, high confidence, observation)_
* Human-1M spans both in-the-wild and studio environments, capturing real-world and curated human work.[^SRC-KB-0021] _(unreviewed, high confidence, observation)_

# Seen in

* [nvidia/PhysicalAI-Human-1M-100K](../references/SRC-KB-0021.md) (2026-11-07)

# Related

[BLS Occupational Outlook Handbook](../concepts/bls-occupational-outlook-handbook.md), [Task Clusters](human-1m/task-clusters.md), [Quality Gates](human-1m/quality-gates.md), [Robot Motion Retargeting](../topics/robot-motion-retargeting.md), [3D Reconstruction](../topics/3d-reconstruction.md), [Head Pose Tracking](../topics/head-pose-tracking.md), [Hand Tracking](../topics/hand-tracking.md), [Stereo](../topics/stereo.md), [Egocentric Video](../topics/egocentric-video.md), [T2](human-1m/t2.md), [T1](human-1m/t1.md), [Lerobot](../tools/lerobot.md), [NVIDIA](../companies/nvidia.md), [PhysicalAI-Human-1M-100K](physicalai-human-1m-100k.md)

[^SRC-KB-0021]: [nvidia/PhysicalAI-Human-1M-100K](../references/SRC-KB-0021.md)
