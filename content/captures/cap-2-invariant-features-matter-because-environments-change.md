---
kind: "capture"
id: "CAP-2"
title: "Invariant features matter because environments change"
generated: true
detail_page: "capture-cap-2.html"
public_url: ""
notion_url: "https://www.notion.so/33764dbaf92b81c3bfa8e632bc6caef6"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T22:53:00.000Z"
last_edited_time: "2026-04-03T22:53:00.000Z"
type: "Highlight"
status: "Used"
summary: "The paper frames causal representations as the abstraction that survives domain shift when superficial correlations do not."
---

# Invariant features matter because environments change

## Summary

The paper frames causal representations as the abstraction that survives domain shift when superficial correlations do not.

## Excerpt

> "Causal models can be seen as the correct abstraction level for generalizing across domains."

## Why It Matters

This is the core bridge from causal modeling to robust ML. It explains why invariance is the target rather than mere predictive fit.

## Source Context

### [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

Schölkopf, Locatello, Bauer, Ke, Kalchbrenner, Goyal, Bengio (2021) · 1/1 ch.

Causal models provide the right abstraction for robust, transferable representations — the ICM principle bridges causality and representation learning.

## Spawned Atoms

### [Causal representations should be invariant across environments](../atoms/atm-1-causal-representations-should-be-invariant-across-environments.md)

concept · Toward Causal Representation Learning

Representations that capture true causal structure remain stable under distribution shift, unlike purely statistical features that exploit spurious correlations.

> "Causal models can be seen as the correct abstraction level for generalizing across domains."

The ICM principle states causal generative mechanisms are autonomous modules — changing one does not affect others. Representations aligned with these mechanisms inherit their invariance.

## Used In Artifacts

### [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)

Slide Deck · Shipped

Full paper: Sections 1-6 covering ICM, disentanglement critique, multi-env supervision, and CRL roadmap

+18 pts
