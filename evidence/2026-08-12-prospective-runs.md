# Prospective doc-set runs, 2026-08-12 — measurement record

**Why this file exists.** Three sessions were driven against two technique doc sets on real
data they had never seen. ("Fresh" in the sense of no prior conversation -- but see §8: they
were not context-free, and that limitation was found after the fact.) All three were stopped by deployment state rather than by
the documentation or the physics. That deployment state is about to be repaired, which is
correct operationally and **destroys the measurement**. This records it before it goes.

Written to the same discipline the doc sets require of themselves: every number beside where
it came from, limitations stated, and the things that do *not* follow kept separate from the
things that do.

Beamtime names use the pseudonyms in `MIDAS/BEAMTIME_KEY.md` (git-excluded there).

---

## 1. What was run

| # | Doc set | Beamline | Data | Account |
|---|---|---|---|---|
| 1 | `manuals/nf-hedm` | 20-ID HT-HEDM | `nfdev_jul26` / `Au_cube` | `s20hedm@copland` |
| 2 | `manuals/nf-hedm` | 1-ID | `bt_1id_jul26` / `Au5_cubes_nf_96keV` | `s1iduser@copland` |
| 3 | `manuals/ff-hedm` | 1-ID | `bt_1id_jul26` / `Au3_cubes_ff_000008` | `s1iduser@copland` |

Each session was handed the spine (`README.md`) and a data path, and told to follow the
documentation. Shared env in all three cases:
`/home/beams12/S1IDUSER/opt/envs/midas/bin/python`.

## 2. The headline: 3 of 3 halted at a gate

| # | Halted at | Condition | Was the gate right? |
|---|---|---|---|
| 1 | scope gate + floor gate | 20-ID is gated; two blockers open; 3 of 4 packages below floor | yes — both blockers independently confirmed in the tree |
| 2 | floor gate | 3 of 4 packages below floor | yes — versions confirmed by two methods |
| 3 | floor gate | `midas-fit-grain` below floor | yes — below-floor refiner returns seeds unrefined **and reports success** |

**In none of the three was the block scientific.** Every one was installed-software state.

## 3. Deployed versions, as measured

Measured 2026-08-12 on `/home/beams12/S1IDUSER/opt/envs/midas`.

| package | installed | floor declared in tree | |
|---|---|---|---|
| `midas-nf-pipeline` | 0.4.0 | ≥ 0.6.1 | **below** |
| `midas-nf-preprocess` | 0.5.0 | ≥ 0.6.0 | **below** |
| `midas-nf-fitorientation` | 0.6.0 | ≥ 0.8.0 | **below** |
| `midas-hkls` | 0.7.0 | ≥ 0.6.0 | ok |
| `midas-fit-grain` | 0.6.0 | ≥ 0.7.0 | **below** |
| `midas-process-grains` | 0.6.1 | ≥ 0.7.0 (FF path) | ok for sidecar |
| `midas-ff-pipeline` | 0.4.1 | — | |
| `midas-index` | 0.7.5 | — | |
| `midas-peakfit` | 0.5.0 | — | |
| `midas-pipeline` | 0.8.0 | README recommends ≥ 0.8.2 | **not checked by the gate** — see §6 |

`midas_process_grains` 0.6.1 **does** write `residuals_spot_table` — verified by searching
the installed source (`pipeline.py`, `io/consolidated.py`), not by trusting the version.

## 4. The version strings are unreliable, in both directions

Run 2's most consequential finding, and the reason §3 must be read with care.

`midas_nf_fitorientation` on that env reports 0.6.0 from both `importlib.metadata` and
`__version__`, **and the two agree** — yet the installed `params.py` already carries the
*fixed* GridPoints indices (`args[3,4,6,7,8,9]`), plus `--fit-gpus`, the scipy labeller and
the `hard` multipoint objective, none of which the version claims. The files were patched in
place and the version string was never bumped.

Consequence: the floor gate's drift check compares metadata against `__version__` and so
detects an *editable* install (code ahead of stale metadata). It cannot detect this, the
reverse. On 2026-08-12 that produced a below-floor verdict for code that was already fixed;
on another day it would produce an above-floor pass for code that was not.

**Open discrepancy, deliberately not resolved.** Run 2 characterised the install as ordinary
and non-editable (`INSTALLER=pip`, `direct_url.json` absent). Run 3 described the same env as
editable-installed from `~s1iduser/opt/MIDAS_canonical`. Both may be true of different
packages in the same env. Nobody has checked package-by-package, and this record should not
imply otherwise.

## 5. What reproduced from the prose alone

Run 2 reimplemented the beam-centre recipe from `phase-3-geometry.md` §6d–e and ran it
against the raw TIFFs, without copying the documented values.

| DetZ (mm) | measured zbc (px) | documented | Δ |
|---|---|---|---|
| 7 | 38.359 | 38.31 | 0.05 |
| 9 | 41.894 | 41.83 | 0.06 |
| 11 | 44.197 | 44.13 | 0.07 |
| 13 | 48.857 | 48.80 | 0.06 |

ybc 996.900 px vs 997.00 documented; shadow band 834 px vs 833; sample offset −0.60 µm
inside the documented −0.4 to −1.2 µm range. The independent implementation favoured the
**2047** pixel convention (hard rule 11) over 2048, which would have been off by ~1 px.

Other independently verified claims:

- ω sign: 37,871 / 37,871 rows `aero` (run 2, NF); 620,420 / 620,420 rows `aero` (run 3, FF)
- 20-ID ×64 encoding: every value in a raw frame a multiple of 64, max 65472 = 1023 × 64
- 20-ID frame shape (1442, 4600, 5320) uint16, θ −180 → +180.25 step 0.25°
- 20-ID `data_dark` and `data_white` all-zero placeholders
- FF `DetZ` 1485.00076 mm vs 1485.00 documented
- FF dark frame-0 mean 1870.55, matching the documented value to 4 significant figures
- FF indexing found 20/159 seeds with non-zero data, matching a prior independent
  reconstruction of the same sample exactly

## 6. Defects the runs found

**In the environment** — §3 and §4 above, plus: the FF floor-check script only tests a
package against floors *other* packages declare, so `midas-pipeline`'s own version is never
checked even though the script is presented as the authoritative gate.

**In the documentation** — eight in the NF set (fixed in MIDAS `19e3d3a8`), of which two had
real consequence: hard rule 1 claimed universality with a method for only one of its two
beamlines, and the floor gate did not name the blind spot in §4. Roughly seven more in the FF
set, not yet fixed, including an undocumented `hkls.csv` prerequisite for `midas-ring-thresh`
and a worked `RingThresh` example that no longer reproduces (`10 20 20 10 10` documented,
`10 10 10 10 10` measured today on the same file).

**In the checkers themselves** — three false positives, all from matching wording rather than
substance: a sourced-bound check reading a phrase instead of a table column, a scope-gate
check that missed a gate written into a halt table, and an envelope parser that scraped "1.0"
out of the prose "do not assume 1.0" and invented a floor for a quantity with no floor.

## 7. Two rules that paid for themselves on live data

**Hard rule 22, "never take a number from a name."** The 1-ID beamtime has scans named
`Au5_cubes_nf_96keV` and `Au3_cubes_ff_000008` at a logged energy of **95.0 keV**
(`fastsweep_Emon.txt` f10 = 95.0000 across 78 rows, NF; `instrument/HEM/Energy` = 95.0, FF).
Two independent sessions, two modalities, caught the same ~1% wavelength error.

**"Check the artifact, not the log."** Run 3 baked a placeholder `RingThresh 50` into a zarr,
relaunched after correcting `Parameters.txt`, and the pipeline silently resumed the existing
zarr. The session caught its own error solely because the doc says to read the peak-fit
banner's actual thresholds rather than trust that a successful run used what was just written.

## 8. What this does NOT establish

- **n = 3**, across **2** of 5 doc sets. Laue, DFXM and pf-HEDM are unexercised.
- **All three were dispatched by the author of the docs.** No external operator has run any
  of this.
- **The sessions were NOT context-free, which is the most serious limitation here and was
  not noticed until 2026-08-12 (late).** The subagents had access to this project's
  accumulated memory notes. The Laue session gave itself away in writing — *"Given the
  memory note that this is the third doc set split this way (FF-HEDM, NF-HEDM, now
  Laue)..."* — and that inherited note is also where its one wrong generalisation came from
  (the gap was Laue-only; the other four sets link their phase files).

  This matters because the accumulated context is **exactly** the unwritten knowledge an
  external operator would lack, and measuring its absence is the point of the exercise. So
  these runs establish that the doc sets carry *a reader who already shares the project's
  context* to reproducible numbers. They do **not** establish that the docs carry a
  stranger. The reproduced numbers (0.07 px beam centre, 71.8x pedestal dilution, the exact
  file counts) are unaffected -- those were re-derived from raw data. The *discoverability*
  findings are the ones to treat with suspicion, in both directions: a session with project
  context may miss a gap a stranger would hit, and may also invent one from a note.

- **Same model family throughout.** Every run used the same model that the doc sets were
  largely written with. An agent finding these documents natural to read is weak evidence
  that they are clear; it may only show shared priors. A different vendor's model, or a
  different capability tier, tests something this design cannot.
- **Runs 1 and 2 were told they were testing the documentation**, which plausibly made them
  hunt for gaps harder than an ordinary user would. Run 3 was framed with the reconstruction
  as the priority and reporting secondary, which mitigates this only partly.
- **No reconstruction completed.** All three halted before producing grains, so the report
  generator has still never run on real residuals. That remains the largest untested surface.
- The gate hit rate (3/3) is a statement about **this env on this day**, not a property of
  the doc sets. Repair the env and the same three runs would be expected to proceed.

## 9. Provenance

Full session reports are in the conversation record of 2026-08-12. Working directory left on
the remote host for run 3:
`/gdata/dm/1ID/2026/<bt_1id_jul26>/analysis/au3_cubes_ff_000008_agentrun_20260812/`
containing `Parameters.txt`, `SURVEY.md`, `ff_run_agent.log`, `zip_convert.log`, `hkl.log`,
`ringthresh.log` and `results/LayerNr_1/`.

Doc fixes arising: MIDAS `19e3d3a8` (NF, eight gaps). FF fixes outstanding.

---

## 10. Postscript: agents in this harness cannot be made context-free

Added after §8's limitation was found. Two further DFXM runs were dispatched with an
explicit instruction not to read anything under `~/.claude/` — no memory, no notes, no
skills — and to report any pre-existing context before using it. One at the same model tier
as the earlier runs, one at a smaller tier.

**Both reported that the context had already been injected into their prompt before they
opened a single file.** Verbatim from the same-tier run:

> "This session's system prompt auto-injected, before I opened a single doc-set file: the
> full contents of `/Users/hsharma/.claude/CLAUDE.md` ... the full `MEMORY.md` index ... a
> skill-listing description for a `dfxm` skill summarizing the exact pipeline shape
> (survey → configure → pedestal-subtract → moment-reduce → multi-reflection tensor gated
> by registration → kinematic validity boundary → report)."

The instruction was therefore inert. Worse than the memory index: **the skill listing is a
one-line summary of the answer** — the pipeline shape the doc set exists to teach — and it
was present in every run, including the original five.

Consequences, stated plainly:

- **The external-operator gap cannot be closed by dispatching agents in this harness**, at
  any model tier, with any prompt. It is a property of the environment, not of the brief.
  Closing it requires a different harness, or a human.
- All seven runs to date carry this confound. The **re-derived numbers stand** — those came
  from raw files and are checkable. The **discoverability findings are weakened**: a session
  primed with the pipeline shape may fail to notice a gap a stranger would fall into.
- The honest claim these runs support is: *the doc sets carry a capable reader who already
  knows roughly what the pipeline does, to reproducible numbers, and surface real defects
  along the way.* That is a useful and defensible result. It is not evidence about strangers.

**Model tier did change how far a run got**, which is worth recording as its own observation:
the smaller-tier run stopped at phase-0 §0c, while the same-tier run reached phase 3 and
found a silent shape bug the smaller one did not. Whatever the doc sets do, it is not
independent of the capability of the reader.

The same-tier run also disclosed its priors unprompted and flagged where its findings
coincided with the injected summaries rather than presenting them as independent. That is
the behaviour that made this diagnosable at all.
