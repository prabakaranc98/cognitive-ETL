---
kind: "atom"
id: "ATM-4"
title: "Multi-environment data provides the supervision signal for causal representation learning"
generated: true
detail_page: "atom-atm-4.html"
public_url: ""
notion_url: "https://www.notion.so/Multi-environment-data-provides-the-supervision-signal-for-causal-representation-learning-33764dbaf92b81d1aefdfe8357611ebe"
domains:
  - "causal inference"
  - "deep learning"
created_time: "2026-04-03T19:34:00.000Z"
last_edited_time: "2026-04-03T21:12:00.000Z"
type: "mechanism"
confidence: "4 - Strong"
reuse_count: 0
---

# Multi-environment data provides the supervision signal for causal representation learning

## Definition

Observing data across multiple environments provides the contrastive signal to identify causal vs. spurious features — causal features stay stable, spurious ones shift.

## Source Quote

> "Distribution shifts correspond to local interventions on the causal model, providing a natural supervision signal."

## Because

Single-environment data is ambiguous — both causal and spurious features predict equally well. Multiple environments break this symmetry because only invariant features persist.

## Boundaries

Requires sufficient diversity in environments. If environments only vary along non-informative dimensions, the signal is too weak.

## Source Context

- [Toward Causal Representation Learning](../sources/src-1-toward-causal-representation-learning.md)

## Related Atoms

- [Causal representations should be invariant across environments](atm-1-causal-representations-should-be-invariant-across-environments.md)

## Used In Artifacts

- [Toward CRL: Schölkopf et al. 2021 — Key Claims & Architecture](../artifacts/art-1-toward-crl-sch-lkopf-et-al-2021-key-claims-architecture.md)
