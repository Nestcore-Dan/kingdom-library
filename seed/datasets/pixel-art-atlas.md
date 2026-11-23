---
type: Dataset
title: Pixel Art Atlas
description: "A dataset of 1.4 million synthetic pixel art sprites with English captions, generated using Krea 2 Turbo and a pixel art LoRA."
tags: [Datasets, "Training & fine-tuning", Vision]
status: stable
sources:
  - { id: SRC-KB-0017, resource: "/references/SRC-KB-0017.md", title: Angais/pixel-art-atlas-1.4m }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T19:42:09+11:00" }
x-kb-kind: dataset
x-kb-slug: pixel-art-atlas
x-kb-origin: auto
x-kb-aliases: [pixelartatlas14m]
x-kb-relevance: core
---

A dataset of 1.4 million synthetic pixel art sprites with English captions, generated using Krea 2 Turbo and a pixel art LoRA.

# Principles

* AI-generated datasets can be used for training and evaluation, but captions may not always accurately describe the generated images.[^SRC-KB-0017] _(unreviewed, high confidence, observation)_
* Captions in AI-generated datasets should be treated as approximate labels and verified visually before use.[^SRC-KB-0017] _(unreviewed, high confidence, claim)_
* AI-generated datasets can be filtered and split for training and validation purposes, but validation subjects may not be unseen in training.[^SRC-KB-0017] _(unreviewed, moderate confidence, analysis)_
* AI-generated datasets can be distributed under open licenses like CC0, but do not override the original model's licensing terms.[^SRC-KB-0017] _(unreviewed, low confidence, hypothesis)_

# Tool-specific tips

* Load the dataset using the Hugging Face `datasets` library with streaming enabled for efficient iteration.[^SRC-KB-0017] _(unreviewed, high confidence, observation)_
* Extract the ZIP and use `tokens.npy` and `palette.npy` to reconstruct RGBA images from pixel data.[^SRC-KB-0017] _(unreviewed, high confidence, observation)_
* The dataset includes a validation split, but it is not guaranteed to contain unseen subjects.[^SRC-KB-0017] _(unreviewed, moderate confidence, analysis)_

# Seen in

* [Angais/pixel-art-atlas-1.4m](../references/SRC-KB-0017.md) (2026-11-06)

# Related

[ai-generated](../topics/ai-generated.md), [synthetic](../topics/synthetic.md), [sprites](../topics/sprites.md), [pixel-art](../topics/pixel-art.md), [Krea](../companies/krea.md), [Krea 2 Turbo](../tools/krea-2-turbo.md), [Angais](../people/angais.md)

[^SRC-KB-0017]: [Angais/pixel-art-atlas-1.4m](../references/SRC-KB-0017.md)
