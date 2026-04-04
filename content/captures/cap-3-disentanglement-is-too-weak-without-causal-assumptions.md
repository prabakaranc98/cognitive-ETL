---
kind: "capture"
id: "CAP-3"
title: "Disentanglement is too weak without causal assumptions"
generated: true
detail_page: "capture-cap-3.html"
public_url: ""
notion_url: "https://www.notion.so/Disentanglement-is-too-weak-without-causal-assumptions-33764dbaf92b816e8ad3c94e7cd268a4"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T22:53:00.000Z"
last_edited_time: "2026-04-03T22:53:00.000Z"
type: "Reflection"
status: "Used"
summary: "The paper’s critique is that statistical factorization alone cannot recover variables that support intervention and transfer."
---

# Disentanglement is too weak without causal assumptions

## Summary

The paper’s critique is that statistical factorization alone cannot recover variables that support intervention and transfer.

## Excerpt

> "Without further assumptions, unsupervised disentanglement is fundamentally impossible."

## Why It Matters

This blocks a common shortcut in representation learning and forces the system toward structural assumptions instead of aesthetic latent spaces.

## Source Context

### [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

Schölkopf, Locatello, Bauer, Ke, Kalchbrenner, Goyal, Bengio (2021) · 1/1 ch.

Causal models provide the right abstraction for robust, transferable representations — the ICM principle bridges causality and representation learning.

## Spawned Atoms

### [Disentanglement alone is insufficient without causal structure](../atoms/atm-3-disentanglement-alone-is-insufficient-without-causal-structure.md)

critique · Toward Causal Representation Learning

Learning statistically independent latent factors does not guarantee that factors correspond to true causal variables or support interventional reasoning.

> "Without further assumptions, unsupervised disentanglement is fundamentally impossible."

Disentanglement methods optimize for statistical independence, but independent components can be rotated arbitrarily without changing the likelihood. Only causal structure breaks this symmetry.

## Used In Artifacts

### [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)

Slide Deck · Shipped

Full paper: Sections 1-6 covering ICM, disentanglement critique, multi-env supervision, and CRL roadmap

+18 pts
