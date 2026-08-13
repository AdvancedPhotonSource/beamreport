# Fixture report — echo/recompute checker validation

Ground truth for this fixture is fixed by construction:

* `0.98492` appears in a tool output only            -> must be RECOMPUTED
* `76.12` appears in a tool output only              -> must be RECOMPUTED
* `66.3` appears in the doc set only                 -> must be ECHOED
* `71.8` appears in the doc set only                 -> must be ECHOED
* `0.999858` appears in both doc set and tool output -> must be RECOMPUTED (tool wins)
* `42.4242` appears in neither                       -> must be UNTRACEABLE

## Reduction

The median-floor pedestal share is `f_ped = 0.98492`, and the directly measured
centroid dilution on these frames is 76.12x.

The documented predicted dilution for this scan is 66.3x, and a previously reported
direct measurement on the same scan gave 71.8x.

The injection-recovery gain came out at 0.999858 on the first motor axis.

An unrelated quantity of 42.4242 is quoted here with no support anywhere.
