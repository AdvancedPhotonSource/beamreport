# Writing a beamreport adapter

**Audience:** a group with an existing analysis pipeline who wants reports out of it.
**Effort:** 50 to 100 lines. One afternoon, assuming your residuals exist.
**Prerequisite:** read [`SPEC.md`](SPEC.md) §1–3 first. This file is the mechanical part only.

Your adapter lives in **your** repository, not in `beamreport`. That boundary is deliberate:
it keeps `beamreport` from accumulating everyone's file formats, and it keeps you free to
change your output layout without waiting on us.

---

## 1. Before you write anything: the residual audit

Answer this first, because it decides which report you can build.

```
Does your fit compute a per-observation misfit?              almost certainly yes
Does it SAVE that misfit, signed, with its coordinates?      usually no
```

Find the place in your fitting code where the model is compared against the data. The quantity
being reduced into a chi-squared is what we need, **before** it is squared and summed.

- **It is saved** → you can build a diagnostic report today. Continue to §2.
- **It is computed and dropped** → add a dozen lines to persist it. This is the single highest
  value change in the whole exercise, and it is worth doing even if you never build a report.
- **It genuinely does not exist** (your method has no per-observation comparison) → you can
  still build a descriptive report. Skip §3, supply objects 1–3, and say so on the page.

---

## 2. The three easy objects

```python
from beamreport import Results, Quality, Provenance

def load_results(run_dir):
    tbl = ...                       # your own loader
    return Results(
        object_id = tbl["id"],
        columns   = {
            "position_x": (tbl["x"], "um"),      # (values, unit) — unit is REQUIRED
            "position_y": (tbl["y"], "um"),
            "tau":        (tbl["tau"], "s"),
        },
    )

def load_quality(run_dir):
    return Quality(
        values    = ...,            # one float per object, higher is better
        name      = "explained variance",
        threshold = 0.5,            # below this you would not quote the object
    )

def load_provenance(run_dir):
    return Provenance(
        inputs     = [...],         # paths that were read
        parameters = run_dir/"params.txt",
        command    = " ".join(sys.argv),
        code_version = ...,
    )
```

Units are required, not optional. A column with no unit is refused (SPEC §8.1) rather than
rendered with a guess.

---

## 3. The sidecar: the only part that takes thought

One row per **observation**, not per object. The whole job is labelling each column with a
role.

```python
from beamreport import Sidecar

def load_sidecar(run_dir):
    obs = ...                       # your per-observation array, (N, K)

    return Sidecar(
        table   = obs,
        columns = ["object_id", "obs_id", "q",      "delay",  "detector_region",
                   "d_amplitude", "d_phase", "weight"],
        units   = ["",          "",       "1/nm",   "s",      "",
                   "counts",      "rad",     ""],
        roles   = ["id",        "aux",    "coord",  "coord",  "coord",
                   "residual",    "residual", "weight"],
    )
```

### Getting the roles right

**`coord`** — every axis along which a systematic could plausibly organise itself. Be generous.
An unused coordinate costs one extra panel; a missing one hides a systematic. If you have ever
said "let me plot the residual against X to check", X is a coordinate.

**`residual`** — signed, in physical units, one column per independent channel.

- Do **not** square them. The sign is what separates a common offset from symmetric scatter,
  and it is the single most useful bit in the file.
- Do **not** sum or average them. Per-observation is the point.
- Do **not** normalise by uncertainty here. Put the uncertainty in `weight` and let the
  diagnostics decide.

**`id`** — must match `object_id` in your result table, or the per-object aggregation silently
produces nonsense. Assert this in your adapter.

### Rollups are optional

If your sidecar is very large you can pre-bin along each coordinate and ship the rollups
instead of, or alongside, the raw table. The diagnostics use rollups when present and the full
table when not. Start without them.

---

## 4. Wire it up

```python
from beamreport import build

build(
    results    = load_results(run_dir),
    quality    = load_quality(run_dir),
    provenance = load_provenance(run_dir),
    sidecar    = load_sidecar(run_dir),          # omit for a descriptive report
    figures    = my_figures(run_dir),            # yours; see §5
    reference  = "docs/diagnosis_reference.md",  # yours; see SPEC §6
    out        = run_dir/"report.html",
)
```

---

## 5. What stays yours

**Your figures.** `beamreport` embeds and lays out figure plates; it does not draw your
science. Hand it rendered images plus a structured caption. Keep spatial maps at true scale
(SPEC §8.4) — the builder refuses non-equal aspect on anything declared spatial.

**Your diagnosis reference.** The prose table mapping symptom to discriminating test to cause
to lever. Three entries is a working start. Without it you get a correct, well-typeset page
with no findings, which is a fair description of where most automated reporting stops.

**Your nulls.** What the same analysis returns on data that cannot contain the effect.

---

## 6. Checklist before you run it

- [ ] Residual audit answered; sidecar exists or descriptive-only is a conscious choice
- [ ] Every result column carries a unit
- [ ] `id` values in the sidecar match `object_id` in the result table (asserted, not assumed)
- [ ] Residuals are signed and unsquared
- [ ] At least two coordinate axes declared
- [ ] Quality threshold set to a value you would actually defend
- [ ] Provenance points at files that exist on the machine that will build the report
- [ ] Build runs where the data lives, not over a network mount, and not in `/tmp`

---

## 7. First run: what to expect

The first report on a dataset you know well is a test of the adapter, not of your science.
Read it against what you already believe about that dataset.

- Findings you agree with → the roles are labelled correctly.
- Findings that are obviously wrong → usually a coordinate mislabelled as a residual, or an
  `id` mismatch. Check those two before anything else.
- **No findings at all** → either the data is clean, or your diagnosis reference is empty.
  Those look identical on the page and are not the same thing. The page says which.
