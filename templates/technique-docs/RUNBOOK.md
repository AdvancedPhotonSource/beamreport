# <TECHNIQUE> runbook — operational state

> **This is the volatile document.** The handbook is procedure and changes slowly; the
> notebook only grows. This file describes *right now*. **Update §R3 before you finish.**

## R1. Where it runs

| | |
|---|---|
| environment | <full path — do not assume anything is on PATH> |
| hosts | <name: what it has, what it is for> |
| long jobs | <how to survive a hangup> |
| outputs | <where they go — and never /tmp> |

## R2. What healthy looks like

**There is no single number for "healthy".** A runbook that publishes one threshold
produces false alarms on the heavy measurements and silence on the broken ones. Every row
below carries the conditions it was measured under; outside those it is not a
specification.

| quantity | value | measured on / conditions |
|---|---|---|
| <quantity> | <value> | <dataset, instrument, settings> |

### R2c. Ranges that are NOT thresholds

<!-- Accuracies, spreads and cross-implementation disagreements. The point of this table
     is to stop someone quoting a number to more precision than the method has. -->

## R3. Current pick-up point

> **Every session updates this before it ends.** A stale pick-up point is worse than none.

**Last updated: <YYYY-MM-DD>.**

**State.** <What is done and verified.>

**Open, not blocking:** <numbered list>

**Mid-run:** <jobs, hosts, log paths — or "nothing".>
