# Project Charter

## Product

A standalone deterministic, local-first authority and effect-control plane for AI agents.

## Boundary

LAC is not an LLM, inference runtime, agent loop, cognition system, memory system, workflow engine, AI OS, generic secret manager, or general observability platform.

## v1 reference harness

Pi is the sole reference harness for the active LAC v1 roadmap.

The governed reference path is:

`local model -> Pi -> LAC permission-aware authority/effect path -> governed effects`

A Pi process is represented as LAC-governed only when started through the qualified LAC launch/profile. Ordinary standalone Pi remains separately runnable outside LAC governance.

## Reuse rule

Reuse mature upstream enforcement components where they satisfy binding requirements. Build only the missing authority/effect semantics. Prefer upstream dependency, then wrapper, then minimal patch, then derivative; do not fork for convenience.

## Current objective

Join the accepted real Pi path to the accepted Phase 4 permission-management/external-consumer path, then validate that combined path through owner UAT and deterministic conformance before v1 productization.

## Controlling specification

`docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` plus accepted ADRs are the controlling planning baseline. Concise operating documents do not supersede them.
