---
type: Reference
title: Digitaluz/uzbek-language-corpus
description: "A cleaned Uzbek language corpus for language-model pretraining: **5,637,052 documents, 6,062,245,161 words**, in Latin and Cyrillic script."
resource: "https://huggingface.co/datasets/Digitaluz/uzbek-language-corpus"
tags: [Datasets]
status: stable
sources:
  - { id: SRC-KB-0018, resource: "https://huggingface.co/datasets/Digitaluz/uzbek-language-corpus", title: Digitaluz/uzbek-language-corpus, author: "huggingface:Digitaluz", last_modified: "2026-11-20" }
generated: { by: kb-librarian/qwen3-vl-8b-instruct, at: "2026-11-20T21:01:56+11:00" }
x-kb-src-id: SRC-KB-0018
x-kb-kind: dataset
x-kb-namespace: KB
x-kb-review-status: unreviewed
x-kb-extension: hubwatch
---

A cleaned Uzbek language corpus for language-model pretraining: **5,637,052 documents, 6,062,245,161 words**, in Latin and Cyrillic script. It combines scanned books, newspapers and archive documents (OCR), born-digital books, legal texts, Wikipedia, web pages and public Telegram posts. All texts have undergone cleaning and quality filtering and are annotated with domain, topic and register labels. Personal data has been replaced with typed placeholders such as `[PHONE]` and `[NAME]`.

# Insights

* Corpora can be annotated with metadata such as domain, topic, and register to support downstream tasks like model fine-tuning or research. _(principle; unreviewed, high confidence, observation; about Uzbek language corpus)_
* Corpora for language model pretraining can be built from diverse, mixed-source data including scanned documents, born-digital texts, and web content. _(principle; unreviewed, high confidence, observation; about Uzbek language corpus)_
* Language models can be used to correct OCR errors and assign metadata labels (domain, topic, register) in corpus curation. _(principle; unreviewed, high confidence, observation; about google/gemma-4-31B-it)_
* Language models used for annotation may introduce errors into the metadata labels, which can affect downstream tasks. _(principle; unreviewed, moderate confidence, claim; about google/gemma-4-31B-it)_
* OCR is a critical step in creating corpora from scanned documents, but may introduce errors that require correction with language models. _(principle; unreviewed, high confidence, observation; about OCR)_
* Personal data in corpora must be masked to protect privacy, even when the data is publicly accessible or derived from public sources. _(principle; unreviewed, high confidence, observation; about Personal data masking)_
* The corpus is designed for pretraining and fine-tuning of language models for Uzbek, not for fact-checking or legal verification. _(principle; unreviewed, moderate confidence, claim; about Uzbek language corpus)_
* The quality of a corpus can be affected by the source material, with some sources (like books and archive documents) being over-represented. _(principle; unreviewed, moderate confidence, claim; about Uzbek language corpus)_

# Covers

* [Digitaluz](../companies/digitaluz.md) - company, core
* [Uzbek language corpus](../datasets/uzbek-language-corpus.md) - dataset, core
* [Telegram](../services/telegram.md) - service, core
* [Latin script](../topics/latin-script.md) - topic, core
* [Cyrillic script](../topics/cyrillic-script.md) - topic, core
* [Tahrirchi](../companies/tahrirchi.md) - company, supporting
* [Uzarchive](../companies/uzarchive.md) - company, supporting
* [Ziyonet/Ziyouz](../companies/ziyonet-ziyouz.md) - company, supporting
* [Lex.uz](../companies/lex-uz.md) - company, supporting
* [Academy of Sciences](../companies/academy-of-sciences.md) - company, supporting
* [Subordinate Organizations](../companies/subordinate-organizations.md) - company, supporting
* [google/gemma-4-31B-it](../llms/google-gemma-4-31b-it.md) - llm, supporting
* [Wikipedia](../services/wikipedia.md) - service, supporting
* [OCR](../companies/digitaluz/ocr.md) - technique, supporting
* [Personal data masking](../companies/digitaluz/personal-data-masking.md) - technique, supporting
* [DeepSeek-OCR](../tools/deepseek-ocr.md) - tool, supporting
* [Microsoft Azure AI Document Intelligence](../tools/microsoft-azure-ai-document-intelligence.md) - tool, supporting

# Our rating

Excellent (assessed by model (draft)). KB house rules R4 - see the house rules.
