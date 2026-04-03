---
kind: "atom"
id: "ATM-3"
title: "Disentanglement alone is insufficient without causal structure"
generated: true
detail_page: "atom-atm-3.html"
public_url: ""
notion_url: "https://www.notion.so/Disentanglement-alone-is-insufficient-without-causal-structure-33764dbaf92b81e79a3dd7a7d4020142"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T19:34:00.000Z"
last_edited_time: "2026-04-03T19:34:00.000Z"
type: "critique"
confidence: "5 - Certain"
reuse_count: 0
---

# Disentanglement alone is insufficient without causal structure

## Definition

Learning statistically independent latent factors does not guarantee that factors correspond to true causal variables or support interventional reasoning.

## Source Quote

> "Without further assumptions, unsupervised disentanglement is fundamentally impossible."

## Because

Disentanglement methods optimize for statistical independence, but independent components can be rotated arbitrarily without changing the likelihood. Only causal structure breaks this symmetry.

## Boundaries

If true causal variables happen to be statistically independent, disentanglement may approximately recover them. But this is a special case.

## Source Context

- [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

## Related Atoms

- [Causal representations should be invariant across environments](atm-1-causal-representations-should-be-invariant-across-environments.md)
- [The Independent Causal Mechanisms principle: causal generative processes are modular and autonomous](atm-2-the-independent-causal-mechanisms-principle-causal-generative-processes-are-modular-and-autonomous.md)

## Used In Artifacts

- [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)
