# Project Charter

## Product

A standalone deterministic, local-first authority and effect-control plane for AI agents.

## Boundary

LAC is not an LLM, inference runtime, agent loop, cognition system, memory system, workflow engine, AI OS, generic secret manager, or general observability platform.

## Initial integration target

`FreeToken -> Pi -> LAC -> governed local effects`

## Reuse rule

Reuse mature upstream enforcement components where they satisfy binding requirements. Build only the missing authority/effect semantics. Prefer upstream dependency, then wrapper, then minimal patch, then derivative; do not fork for convenience.

## Phase 0 objective

Qualify upstreams and resolve Airlock adoption strategy. Do not implement the controller before ADR-001 is resolved.

## Controlling specification

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` is the owner-provided controlling planning baseline. Concise operating documents do not supersede it.
