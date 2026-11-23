---
type: Reference
title: nvidia/PhysicalAI-Human-1M-100K
description: "Across AI, a common route to scale is **distilling human experience into models**: what people write, see, and create."
resource: "https://huggingface.co/datasets/nvidia/PhysicalAI-Human-1M-100K"
tags: [Datasets, Evaluation, Vision]
status: stable
sources:
  - { id: SRC-KB-0021, resource: "https://huggingface.co/datasets/nvidia/PhysicalAI-Human-1M-100K", title: nvidia/PhysicalAI-Human-1M-100K, author: "huggingface:nvidia", last_modified: "2026-11-07" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0021
x-kb-kind: dataset
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: hubwatch
---

Across AI, a common route to scale is **distilling human experience into models**: what people write, see, and create. The physical AI analogue is **sensorized human data**—egocentric video, dense language annotations, and head and hand pose that connect perception, action, and intent.

# Insights

* 3D reconstruction and robot motion retargeting are key applications enabled by the dataset. _(principle; unreviewed, high confidence, observation; about 3D Reconstruction, Robot Motion Retargeting)_
* Distilling human experience into models is a common route to scale in AI. _(principle; unreviewed, high confidence, observation; about PhysicalAI-Human-1M-100K)_
* Diversity at task, scene, collector, and environment levels is a key quality criterion for Human-1M. _(principle; unreviewed, high confidence, observation; about Quality Gates)_
* Episodes are the atomic unit of Human-1M, with strict requirements for video, motion, and language alignment. _(principle; unreviewed, high confidence, observation; about Human-1M)_
* High-quality human demonstrations are essential for training physical AI models. _(principle; unreviewed, high confidence, observation; about Human-1M)_
* Human-1M spans both in-the-wild and studio environments, capturing real-world and curated human work. _(principle; unreviewed, high confidence, observation; about Human-1M)_
* Motion annotations (head pose, hand keypoints) are critical for aligning perception with action in physical AI. _(principle; unreviewed, high confidence, observation; about Head Pose Tracking, Hand Tracking)_
* Sensorized human data (egocentric video, dense language, motion) is the physical AI analogue of distilled human experience. _(principle; unreviewed, high confidence, observation; about PhysicalAI-Human-1M-100K)_
* T1 and T2 annotations provide structured, timed language descriptions of human actions for AI training. _(principle; unreviewed, high confidence, observation; about T1, T2)_
* The dataset is organized by vendor, batch, and version for scalable and reproducible access. _(principle; unreviewed, high confidence, observation; about Lerobot)_

# Covers

* [NVIDIA](../companies/nvidia.md) - company, core
* [T1](../datasets/human-1m/t1.md) - concept, core
* [T2](../datasets/human-1m/t2.md) - concept, core
* [Quality Gates](../datasets/human-1m/quality-gates.md) - concept, core
* [Task Clusters](../datasets/human-1m/task-clusters.md) - concept, core
* [PhysicalAI-Human-1M-100K](../datasets/physicalai-human-1m-100k.md) - dataset, core
* [Human-1M](../datasets/human-1m.md) - dataset, core
* [Egocentric Video](../topics/egocentric-video.md) - topic, core
* [Stereo](../topics/stereo.md) - topic, core
* [Hand Tracking](../topics/hand-tracking.md) - topic, core
* [Head Pose Tracking](../topics/head-pose-tracking.md) - topic, core
* [3D Reconstruction](../topics/3d-reconstruction.md) - topic, core
* [Robot Motion Retargeting](../topics/robot-motion-retargeting.md) - topic, core
* [BLS Occupational Outlook Handbook](../concepts/bls-occupational-outlook-handbook.md) - concept, supporting
* [Lerobot](../tools/lerobot.md) - tool, supporting

# Our rating

Excellent (assessed by model (draft)). KB house rules R4 - see the house rules.
