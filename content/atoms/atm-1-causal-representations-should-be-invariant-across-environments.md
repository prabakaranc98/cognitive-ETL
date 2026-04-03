---
kind: "atom"
id: "ATM-1"
title: "Causal representations should be invariant across environments"
generated: true
detail_page: "atom-atm-1.html"
public_url: ""
notion_url: "https://www.notion.so/Causal-representations-should-be-invariant-across-environments-33764dbaf92b8111b435f49447d94d2f"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T19:34:00.000Z"
last_edited_time: "2026-04-03T19:34:00.000Z"
type: "concept"
confidence: "4 - Strong"
reuse_count: 0
---

# Causal representations should be invariant across environments

## Definition

Representations that capture true causal structure remain stable under distribution shift, unlike purely statistical features that exploit spurious correlations.

## Source Quote

> "Causal models can be seen as the correct abstraction level for generalizing across domains."

## Because

The ICM principle states causal generative mechanisms are autonomous modules — changing one does not affect others. Representations aligned with these mechanisms inherit their invariance.

## Boundaries

Assumes the causal graph is stable across environments. Breaks under structural causal changes. Also assumes we can identify the correct causal variables.

## Source Context

- [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

## Related Atoms

- [The Independent Causal Mechanisms principle: causal generative processes are modular and autonomous](atm-2-the-independent-causal-mechanisms-principle-causal-generative-processes-are-modular-and-autonomous.md)
- [Multi-environment data provides the supervision signal for causal representation learning](atm-4-multi-environment-data-provides-the-supervision-signal-for-causal-representation-learning.md)

## Used In Artifacts

- [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)
