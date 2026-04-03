---
kind: "capture"
id: "CAP-1"
title: "ICM as the paper's backbone assumption"
generated: true
detail_page: "capture-cap-1.html"
public_url: ""
notion_url: "https://www.notion.so/33764dbaf92b813e9682eeb263905a76"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T22:52:00.000Z"
last_edited_time: "2026-04-03T22:52:00.000Z"
type: "Rough Synthesis"
status: "Used"
summary: "The paper treats independent causal mechanisms as the structural reason causal representations can generalize."
---

# ICM as the paper's backbone assumption

## Summary

The paper treats independent causal mechanisms as the structural reason causal representations can generalize.

## Excerpt

> "The mechanisms of the causal generative model are autonomous and do not inform or influence each other."

## Why It Matters

Without an explicit mechanism story, the representation-learning claim collapses back into pattern matching.

## Source Context

### [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

Schölkopf, Locatello, Bauer, Ke, Kalchbrenner, Goyal, Bengio (2021) · 1/1 ch.

Causal models provide the right abstraction for robust, transferable representations — the ICM principle bridges causality and representation learning.

## Spawned Atoms

### [The Independent Causal Mechanisms principle: causal generative processes are modular and autonomous](../atoms/atm-2-the-independent-causal-mechanisms-principle-causal-generative-processes-are-modular-and-autonomous.md)

mechanism · Toward Causal Representation Learning

Each mechanism in a causal system operates independently — changing one mechanism does not alter the others.

> "The mechanisms of the causal generative model are autonomous and do not inform or influence each other."

Nature's generative process factorizes into independent modules corresponding to edges in the causal graph. This is a structural assumption about how the world generates data.

## Used In Artifacts

### [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)

Slide Deck · Shipped

Full paper: Sections 1-6 covering ICM, disentanglement critique, multi-env supervision, and CRL roadmap

+18 pts
