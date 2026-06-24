# Intent — L3b Harness Routing: opencode-style Coding Agent

## Goal

Demonstrate the opencode-style "escalate-on-failure" harness routing pattern for coding tasks:
a multi-step loop where a cheap model attempts code generation first, unit tests run against
the output, and escalation to a strong model happens only on failure (with the failing code as
context). Compare all-cheap, all-strong, and routed harnesses on accuracy and cost.

## Hypothesis

The routed harness should land between all-cheap and all-strong on cost while staying at or
near all-strong accuracy. On tasks where cheap fails, the strong model gets a repair prompt
with debugging context (failing code), making escalation more efficient than a cold strong call.

## Why this matters

This is the primary model-routing pattern used by production coding agents (opencode, Aider,
Claude Code's sub-agent dispatch). It is "harness routing" rather than "query routing": the
routing decision is made at runtime by observing test outcomes rather than predicting difficulty
from the prompt text. It avoids oracle leakage: the router never sees difficulty labels — it
only sees whether the grader returned pass or fail.

## Honest-result commitment

If cheap already solves all tasks, the routed harness will match cheap cost exactly. This is a
valid and instructive finding — it confirms the escalation guard adds zero overhead when cheap
suffices, and that the real routing opportunity on this corpus is in math (not coding).
