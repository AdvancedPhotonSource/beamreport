"""Technique-independent diagnostics.

Everything here works from the `coord` / `residual` / `id` role declaration in a
Sidecar and knows nothing about any measurement technique. The tests answer questions
of the form "does this misfit organise itself along some axis, or is it noise", which
is the same question whether the axis is an azimuth, a delay time, or a detector
region.

Detection generalises. Interpretation does not: these functions emit symptom codes and
numbers, never causes or levers.

numpy only, by design (see pyproject.toml).
"""

from __future__ import annotations

import numpy as np

from .finding import Finding, fmt

# --------------------------------------------------------------------------- helpers

ANGULAR_UNITS = {
    "deg": 360.0, "degree": 360.0, "degrees": 360.0, "°": 360.0,
    "rad": 2 * np.pi, "radian": 2 * np.pi, "radians": 2 * np.pi,
}


def _period_for(unit: str) -> float | None:
    """Full-turn period for an angular unit, else None.

    A coordinate is treated as angular only when its declared unit says so. Guessing
    from the value range would misfire on, say, a 0-360 second delay axis.
    """
    return ANGULAR_UNITS.get((unit or "").strip().lower())


def _bic(rss: float, n: int, k: int) -> float:
    """Gaussian BIC. Lower is better."""
    if n <= k or rss <= 0:
        return np.inf
    return n * np.log(rss / n) + k * np.log(n)


def _lstsq(A: np.ndarray, y: np.ndarray):
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    rss = float(np.sum((y - A @ coef) ** 2))
    return coef, rss


def mad(x: np.ndarray) -> float:
    """Median absolute deviation, scaled to be comparable with a standard deviation."""
    x = x[np.isfinite(x)]
    if x.size == 0:
        return float("nan")
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def group_median(ids: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Median of `values` within each unique id. Returns (unique_ids, medians)."""
    uniq = np.unique(ids)
    out = np.array([np.median(values[ids == u]) for u in uniq], dtype=float)
    return uniq, out


# ----------------------------------------------------------------------- trend tests


def fit_trend(coord: np.ndarray, resid: np.ndarray, unit: str = "") -> dict:
    """Fit constant / linear / (if angular) periodic, and report which is supported.

    Model choice is by BIC rather than by eye, so the same data always yields the same
    verdict. `amplitude` is the peak-to-centre excursion of the winning model in the
    residual's own units, which is the number a reader can act on.
    """
    m = np.isfinite(coord) & np.isfinite(resid)
    c, r = coord[m], resid[m]
    n = c.size
    out = {"n": n, "model": "constant", "amplitude": 0.0, "params": {}, "bic": {}}
    if n < 8:
        out["model"] = "insufficient"
        return out

    ones = np.ones_like(c)

    _, rss_c = _lstsq(ones[:, None], r)
    out["bic"]["constant"] = _bic(rss_c, n, 1)

    span = float(np.ptp(c))
    if span > 0:
        coef_l, rss_l = _lstsq(np.column_stack([ones, c]), r)
        out["bic"]["linear"] = _bic(rss_l, n, 2)
        out["params"]["linear"] = {"intercept": float(coef_l[0]), "slope": float(coef_l[1])}

    period = _period_for(unit)
    if period:
        w = 2 * np.pi / period
        coef_p, rss_p = _lstsq(np.column_stack([ones, np.cos(w * c), np.sin(w * c)]), r)
        out["bic"]["periodic"] = _bic(rss_p, n, 3)
        amp = float(np.hypot(coef_p[1], coef_p[2]))
        phase = float(np.degrees(np.arctan2(coef_p[2], coef_p[1])))
        out["params"]["periodic"] = {"offset": float(coef_p[0]), "amplitude": amp, "phase_deg": phase}

    best = min(out["bic"], key=out["bic"].get)
    out["model"] = best
    if best == "linear":
        out["amplitude"] = abs(out["params"]["linear"]["slope"]) * span / 2.0
    elif best == "periodic":
        out["amplitude"] = out["params"]["periodic"]["amplitude"]

    scatter = mad(r)
    out["scatter"] = scatter
    out["amplitude_over_scatter"] = (
        float(out["amplitude"] / scatter) if scatter and np.isfinite(scatter) else float("nan")
    )
    return out


def amplitude_across(
    coord: np.ndarray, resid: np.ndarray, other: np.ndarray, unit: str = "", n_bins: int = 4
) -> dict:
    """Is a trend's amplitude constant in absolute units, or growing with `other`?

    This is the discrimination that distinguishes a rigid common offset (same absolute
    excursion everywhere) from an effect that scales with the second coordinate. It is
    arithmetic, not judgement, which is why it belongs here rather than in a reference.
    """
    m = np.isfinite(coord) & np.isfinite(resid) & np.isfinite(other)
    c, r, o = coord[m], resid[m], other[m]
    if c.size < 8 * n_bins:
        return {"verdict": "insufficient", "n": int(c.size)}

    edges = np.quantile(o, np.linspace(0, 1, n_bins + 1))
    edges[-1] += 1e-9
    centres, amps = [], []
    for i in range(n_bins):
        sel = (o >= edges[i]) & (o < edges[i + 1])
        if sel.sum() < 8:
            continue
        f = fit_trend(c[sel], r[sel], unit)
        if f["model"] in ("insufficient", "constant"):
            continue
        centres.append(float(np.median(o[sel])))
        amps.append(float(f["amplitude"]))

    if len(amps) < 3:
        return {"verdict": "insufficient", "n_bins_used": len(amps)}

    centres_a, amps_a = np.array(centres), np.array(amps)
    slope = float(np.polyfit(centres_a, amps_a, 1)[0])
    mean_amp = float(np.mean(amps_a))
    # Fractional change in amplitude across the observed span of `other`.
    growth = slope * float(np.ptp(centres_a)) / mean_amp if mean_amp else float("nan")
    verdict = "growing" if abs(growth) > 0.5 else "constant"
    return {
        "verdict": verdict,
        "growth_fraction": growth,
        "mean_amplitude": mean_amp,
        "bin_centres": centres,
        "bin_amplitudes": amps,
    }


# ------------------------------------------------------- systematic versus scatter


def systematic_vs_scatter(ids: np.ndarray, resid: np.ndarray) -> dict:
    """Is the misfit a common offset shared by every object, or per-object spread?

    Resolves more arguments than any other test here. A common offset is an instrument
    or model property and is usually fixable; per-object spread is genuine variation
    and is not a bug.

    `ratio` (|mean| / spread) measures dominance; `t` measures whether the mean is
    distinguishable from zero at all. Both are needed: a tiny but highly significant
    mean is not a common offset worth chasing.
    """
    uniq, med = group_median(ids, resid)
    med = med[np.isfinite(med)]
    n = med.size
    if n < 4:
        return {"verdict": "insufficient", "n_objects": int(n)}

    mean = float(np.mean(med))
    spread = float(np.std(med, ddof=1))
    ratio = abs(mean) / spread if spread > 0 else np.inf
    t = abs(mean) / (spread / np.sqrt(n)) if spread > 0 else np.inf

    if t < 3:
        verdict = "no_common_offset"
    elif ratio >= 1.0:
        verdict = "common_offset"
    else:
        verdict = "mixed"

    return {
        "verdict": verdict,
        "n_objects": int(n),
        "mean": mean,
        "spread": spread,
        "ratio": float(ratio),
        "t": float(t),
    }


def param_residual_correlation(param: np.ndarray, resid_per_object: np.ndarray) -> dict:
    """Does a fitted parameter correlate with its own residual?

    A strong negative correlation means the observations pull against the fitted value:
    the parameter is absorbing misfit rather than being supported by data. Near-zero
    correlation means the data supports the values as fitted.
    """
    m = np.isfinite(param) & np.isfinite(resid_per_object)
    p, r = param[m], resid_per_object[m]
    if p.size < 8 or np.ptp(p) == 0 or np.ptp(r) == 0:
        return {"verdict": "insufficient", "n": int(p.size)}
    rho = float(np.corrcoef(p, r)[0, 1])
    # Fisher z, two-sided, for a rough significance guard.
    z = 0.5 * np.log((1 + rho) / (1 - rho)) * np.sqrt(p.size - 3) if abs(rho) < 1 else np.inf
    verdict = "correlated" if (abs(rho) >= 0.4 and abs(z) >= 3) else "supported"
    return {"verdict": verdict, "rho": rho, "z": float(z), "n": int(p.size)}


# --------------------------------------------------------------- population splits


def _em_two_gaussian(x: np.ndarray, iters: int = 200) -> tuple[float, dict]:
    """Fit a 2-component 1-D Gaussian mixture by EM. Returns (BIC, params)."""
    x = x[np.isfinite(x)]
    n = x.size
    lo, hi = np.quantile(x, [0.25, 0.75])
    mu = np.array([lo, hi], dtype=float)
    if mu[0] == mu[1]:
        return np.inf, {}
    sd = np.full(2, max(np.std(x), 1e-12))
    w = np.array([0.5, 0.5])

    for _ in range(iters):
        p = w * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
        tot = p.sum(1, keepdims=True)
        tot[tot == 0] = 1e-300
        g = p / tot
        nk = g.sum(0)
        if np.any(nk < 2):
            return np.inf, {}
        mu_new = (g * x[:, None]).sum(0) / nk
        sd = np.sqrt((g * (x[:, None] - mu_new) ** 2).sum(0) / nk)
        sd = np.maximum(sd, 1e-12)
        w = nk / n
        if np.allclose(mu_new, mu, rtol=1e-8, atol=1e-12):
            mu = mu_new
            break
        mu = mu_new

    p = w * np.exp(-0.5 * ((x[:, None] - mu) / sd) ** 2) / (sd * np.sqrt(2 * np.pi))
    ll = float(np.sum(np.log(np.maximum(p.sum(1), 1e-300))))
    return -2 * ll + 5 * np.log(n), {
        "means": mu.tolist(), "sds": sd.tolist(), "weights": w.tolist(),
    }


def _density_dip(mu, sd, w, n_grid: int = 512) -> tuple[bool, float]:
    """Does the fitted mixture density actually have two peaks with a valley between?

    A two-component mixture fitting better than one component is NOT bimodality: a
    skewed unimodal distribution is fitted better by two Gaussians whose sum still has
    a single peak. The question a reader is asking is whether there are two
    populations, and that requires a dip in the density, so test for the dip.
    """
    mu, sd, w = np.asarray(mu), np.asarray(sd), np.asarray(w)
    lo, hi = mu.min() - 4 * sd.max(), mu.max() + 4 * sd.max()
    x = np.linspace(lo, hi, n_grid)
    d = np.sum(
        w[:, None] * np.exp(-0.5 * ((x[None, :] - mu[:, None]) / sd[:, None]) ** 2)
        / (sd[:, None] * np.sqrt(2 * np.pi)),
        axis=0,
    )
    peaks = np.flatnonzero((d[1:-1] > d[:-2]) & (d[1:-1] >= d[2:])) + 1
    if peaks.size < 2:
        return False, 0.0
    a, b = sorted(peaks[np.argsort(d[peaks])[::-1]][:2])
    valley = float(d[a : b + 1].min())
    depth = 1.0 - valley / float(min(d[a], d[b]))
    return depth >= 0.10, depth


def bimodality(values: np.ndarray) -> dict:
    """Two populations, or one?

    Three conditions, all required: a two-component mixture must beat one by BIC, the
    components must be separated by at least one pooled standard deviation, and the
    resulting density must actually dip between them. The first alone is not a
    bimodality test, and treating it as one is how a report invents structure that is
    not in the data.
    """
    x = values[np.isfinite(values)]
    n = x.size
    if n < 20:
        return {"verdict": "insufficient", "n": int(n)}

    sd1 = float(np.std(x))
    if sd1 <= 0:
        return {"verdict": "one", "n": int(n)}
    ll1 = float(np.sum(-0.5 * ((x - np.mean(x)) / sd1) ** 2 - np.log(sd1 * np.sqrt(2 * np.pi))))
    bic1 = -2 * ll1 + 2 * np.log(n)

    bic2, params = _em_two_gaussian(x)
    if not np.isfinite(bic2) or bic2 >= bic1:
        return {"verdict": "one", "n": int(n), "bic1": bic1, "bic2": float(bic2)}

    mu, sd, w = params["means"], params["sds"], params["weights"]
    pooled = np.sqrt(np.average(np.square(sd), weights=w))
    sep = abs(mu[1] - mu[0]) / pooled if pooled > 0 else np.inf
    if sep < 1.0:
        return {"verdict": "one", "n": int(n), "separation": float(sep), "reason": "separation"}

    dipped, depth = _density_dip(mu, sd, w)
    if not dipped:
        return {
            "verdict": "one", "n": int(n), "separation": float(sep),
            "dip_depth": depth, "reason": "no dip in the density",
        }
    return {
        "verdict": "two", "n": int(n), "separation": float(sep), "dip_depth": depth,
        "means": mu, "weights": w, "bic1": bic1, "bic2": float(bic2),
    }


def bound_pileup(values: np.ndarray, lo: float, hi: float, shell: float = 0.02) -> dict:
    """Are objects piling up at a declared bound?

    Divergence-to-bound leaves a pile-up AT the bound. An outer shell holding roughly
    nothing refutes it, which is exactly as informative as finding one.
    """
    x = values[np.isfinite(values)]
    if x.size < 20 or hi <= lo:
        return {"verdict": "insufficient", "n": int(x.size)}
    width = (hi - lo) * shell
    frac = float(np.mean((x <= lo + width) | (x >= hi - width)))
    # Expected occupancy if the distribution were uniform across the bounded range.
    verdict = "pileup" if frac > max(4 * shell, 0.05) else "no_pileup"
    return {"verdict": verdict, "shell_fraction": frac, "expected_uniform": 2 * shell, "n": int(x.size)}


def scale_against_expectation(measured: float, expected: float, tol: float = 0.25) -> dict:
    """Compare a recovered magnitude against an independent expectation.

    This is the one class of error a residual-based diagnostic cannot see. When the
    model carries a free amplitude, a multiplicative error is absorbed into the fit and
    the residual stays flat: the map looks smooth, the chi-squared looks fine, and the
    number is wrong by orders of magnitude. Catching it requires a value from outside
    the fit, which is why `expected` is an input and never inferred.
    """
    if not (np.isfinite(measured) and np.isfinite(expected)) or expected == 0:
        return {"verdict": "insufficient"}
    ratio = float(measured / expected)
    if ratio < 1 - tol:
        verdict = "suppressed"
    elif ratio > 1 + tol:
        verdict = "inflated"
    else:
        verdict = "consistent"
    return {"verdict": verdict, "ratio": ratio, "measured": float(measured),
            "expected": float(expected), "tolerance": float(tol)}


def uncertainty_calibration(resid: np.ndarray, sigma: np.ndarray) -> dict:
    """Do the declared uncertainties match the observed scatter?

    chi-squared per degree of freedom, where sigma is a 1-sigma uncertainty in the
    residual's own units. Far from 1 in either direction means every significance
    statement downstream is wrong: too high and real structure is called noise, too low
    and noise is quoted as a detection.
    """
    m = np.isfinite(resid) & np.isfinite(sigma) & (sigma > 0)
    r, s = resid[m], sigma[m]
    if r.size < 20:
        return {"verdict": "insufficient", "n": int(r.size)}
    chi2 = float(np.mean((r / s) ** 2))
    if chi2 > 2.0:
        verdict = "underestimated"        # errors too small for the scatter present
    elif chi2 < 0.5:
        verdict = "overestimated"
    else:
        verdict = "calibrated"
    return {"verdict": verdict, "chi2_per_dof": chi2, "n": int(r.size)}


def at_floor(values: np.ndarray, floor: float, rel_tol: float = 0.1) -> dict:
    """Are recovered values piling up at the pipeline's own floor?

    A fitted value sitting at the resolution floor measures the pipeline, not the
    sample. It is circular: the analysis cannot return anything smaller, so finding the
    smallest possible answer is not evidence of anything. The floor must come from the
    envelope, never from the data being judged.
    """
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if x.size < 20 or not np.isfinite(floor) or floor <= 0:
        return {"verdict": "insufficient", "n": int(x.size)}
    frac = float(np.mean(x <= floor * (1 + rel_tol)))
    return {
        "verdict": "at_floor" if frac > 0.2 else "above_floor",
        "fraction_at_floor": frac, "floor": float(floor), "n": int(x.size),
    }


def clears_null(value: float, null_samples: np.ndarray, side: str = "greater") -> dict:
    """Does a measured quantity clear what the same analysis returns on null data?"""
    ns = np.asarray(null_samples, dtype=float).ravel()
    ns = ns[np.isfinite(ns)]
    if ns.size < 5:
        return {"verdict": "insufficient", "n_null": int(ns.size)}
    if side == "greater":
        p = float(np.mean(ns >= value))
        limit = float(np.max(ns))
    else:
        p = float(np.mean(ns <= value))
        limit = float(np.min(ns))
    return {
        "verdict": "cleared" if p < 0.05 else "not_cleared",
        "value": float(value), "null_p": p, "null_extreme": limit, "n_null": int(ns.size),
    }


# ------------------------------------------------------------------ orchestration


def diagnose(results, sidecar=None, quality=None, bounds=None, nulls=None,
             expectations=None, floors=None) -> list[Finding]:
    """Run every applicable technique-independent test and return Findings.

    All the extra inputs are opt-in, and a test with no declared input is skipped rather
    than guessed at -- an undeclared limit produces no claim.

    - `bounds`       {column: (lo, hi)} for the pile-up test
    - `nulls`        {label: (measured, null_samples)}
    - `expectations` {label: (measured, expected[, tolerance])} from OUTSIDE the fit
    - `floors`       {column: floor} or {column: (floor, provenance)}, from the envelope
    """
    out: list[Finding] = []

    if quality is not None:
        out += _quality_findings(quality)

    if sidecar is not None:
        out += _sidecar_findings(results, sidecar, bounds)

    out += _expectation_findings(expectations)
    out += _floor_findings(results, floors)

    for label, (value, samples) in (nulls or {}).items():
        r = clears_null(value, samples)
        if r["verdict"] == "not_cleared":
            out.append(Finding(
                symptom="null.not_cleared", level="caution",
                title=f"{label} does not clear its null",
                statement=(
                    f"{label} = {fmt(r['value'])}, but {r['null_p'] * 100:.0f}% of "
                    f"{r['n_null']} null realisations reach at least that value "
                    f"(most extreme null {fmt(r['null_extreme'])}). Not quotable."
                ),
                numbers=r,
            ))
    order = {lvl: i for i, lvl in enumerate(("systematic", "caution", "solid"))}
    return sorted(out, key=lambda f: order.get(f.level, 9))


def _expectation_findings(expectations) -> list[Finding]:
    out: list[Finding] = []
    for label, spec in (expectations or {}).items():
        measured, expected, *rest = spec
        r = scale_against_expectation(measured, expected, rest[0] if rest else 0.25)
        if r["verdict"] not in ("suppressed", "inflated"):
            continue
        factor = 1 / r["ratio"] if r["verdict"] == "suppressed" else r["ratio"]
        out.append(Finding(
            symptom=f"scale.{r['verdict']}", level="systematic",
            title=f"{label} is {r['verdict']} against its expectation",
            statement=(
                f"Measured {fmt(r['measured'])} against an expected {fmt(r['expected'])}, "
                f"a factor of {fmt(factor)}. A multiplicative error of this kind is "
                f"invisible to the residual when the model carries a free amplitude, so "
                f"a flat residual is not evidence against it."
            ),
            numbers=r, channel=label,
        ))
    return out


def _floor_findings(results, floors) -> list[Finding]:
    out: list[Finding] = []
    for col, spec in (floors or {}).items():
        if col not in results.columns:
            continue
        floor, prov = spec if isinstance(spec, (tuple, list)) else (spec, "")
        vals = np.asarray(results.columns[col][0], dtype=float)
        r = at_floor(vals, floor)
        if r["verdict"] != "at_floor":
            continue
        src = f" (floor from {prov})" if prov else ""
        out.append(Finding(
            symptom="floor.limited", level="caution",
            title=f"{col} is pinned at the analysis floor",
            statement=(
                f"{r['fraction_at_floor'] * 100:.0f}% of {r['n']} values sit at or below "
                f"{fmt(r['floor'])}{src}. Those values measure the pipeline, not the "
                f"sample: the analysis cannot return anything smaller, so finding the "
                f"smallest possible answer is not evidence about the specimen."
            ),
            numbers=r, coord=col,
        ))
    return out


def _quality_findings(quality) -> list[Finding]:
    out = []
    q = np.asarray(quality.values, dtype=float)
    finite = q[np.isfinite(q)]
    if finite.size:
        out.append(Finding(
            symptom="", level="solid", title=f"{quality.name}",
            statement=(
                f"median {fmt(float(np.median(finite)))} over {finite.size} objects "
                f"(range {fmt(float(finite.min()))} to {fmt(float(finite.max()))})."
            ),
            numbers={"median": float(np.median(finite)), "n": int(finite.size)},
        ))
    if quality.threshold is not None and finite.size:
        below = float(np.mean(finite < quality.threshold))
        if below > 0.2:
            out.append(Finding(
                symptom="quality.low_fraction", level="caution",
                title=f"{below * 100:.0f}% of objects fall below the {quality.name} threshold",
                statement=(
                    f"{below * 100:.0f}% of {finite.size} objects sit below "
                    f"{fmt(quality.threshold)}. They are shown but should not be quoted."
                ),
                numbers={"fraction_below": below, "threshold": quality.threshold},
            ))
    bm = bimodality(finite)
    if bm["verdict"] == "two":
        out.append(Finding(
            symptom="split.bimodal", level="caution",
            title=f"{quality.name} splits into two populations",
            statement=(
                f"Two components separated by {fmt(bm['separation'])} pooled standard "
                f"deviations, carrying {bm['weights'][0] * 100:.0f}% and "
                f"{bm['weights'][1] * 100:.0f}% of objects."
            ),
            numbers=bm, channel=quality.name,
        ))
    return out


def _sidecar_findings(results, sidecar, bounds) -> list[Finding]:
    out: list[Finding] = []
    id_col = sidecar.names("id")[0]
    ids = sidecar.column(id_col)
    coords = sidecar.names("coord")
    units = {n: u for n, u in zip(sidecar.columns, sidecar.units)}

    for ch in sidecar.names("residual"):
        r = sidecar.column(ch)
        r_unit = units.get(ch, "")

        sv = systematic_vs_scatter(ids, r)
        if sv["verdict"] == "common_offset":
            out.append(Finding(
                symptom="systematic.common_offset", level="systematic",
                title=f"{ch}: a common offset shared by every object",
                statement=(
                    f"Per-object medians average {fmt(sv['mean'])} {r_unit} with a spread of "
                    f"{fmt(sv['spread'])} across {sv['n_objects']} objects "
                    f"(|mean|/spread = {fmt(sv['ratio'])}). The offset dominates per-object "
                    f"variation, so it is a property of the instrument or the model, not of "
                    f"the objects."
                ),
                numbers=sv, channel=ch,
            ))
        elif sv["verdict"] == "no_common_offset":
            out.append(Finding(
                symptom="", level="solid",
                title=f"{ch}: no common offset",
                statement=(
                    f"Per-object medians scatter about {fmt(sv['mean'])} {r_unit} with spread "
                    f"{fmt(sv['spread'])} (t = {fmt(sv['t'])}). Consistent with zero; the "
                    f"variation that is present is per-object, not shared."
                ),
                numbers=sv, channel=ch,
            ))
        elif sv["verdict"] == "mixed":
            out.append(Finding(
                symptom="systematic.per_object", level="caution",
                title=f"{ch}: nonzero mean, but per-object scatter dominates",
                statement=(
                    f"Mean {fmt(sv['mean'])} {r_unit} is distinguishable from zero "
                    f"(t = {fmt(sv['t'])}) but is smaller than the {fmt(sv['spread'])} "
                    f"spread between objects. Correcting the mean will move the baseline "
                    f"without reducing the scatter."
                ),
                numbers=sv, channel=ch,
            ))

        # Uncertainty calibration, but only when the declared units make `weight`
        # unambiguously a 1-sigma in the residual's own units. A weight column could
        # equally be 1/sigma^2, and silently guessing between them would produce a
        # chi-squared wrong by orders of magnitude -- exactly the class of convention
        # error the unit declaration exists to prevent.
        for wname in sidecar.names("weight"):
            if units.get(wname, "") != r_unit or not r_unit:
                continue
            uc = uncertainty_calibration(r, sidecar.column(wname))
            if uc["verdict"] in ("underestimated", "overestimated"):
                low = uc["verdict"] == "overestimated"
                out.append(Finding(
                    symptom="uncertainty.miscalibrated", level="systematic",
                    title=f"{ch}: declared uncertainties do not match the scatter",
                    statement=(
                        f"chi-squared per degree of freedom is {fmt(uc['chi2_per_dof'])} "
                        f"over {uc['n']} observations, against 1 for a calibrated error "
                        f"model. The uncertainties are "
                        f"{'too large' if low else 'too small'}, so every significance "
                        f"statement derived from them is "
                        f"{'conservative' if low else 'overstated'}."
                    ),
                    numbers=uc, channel=ch,
                ))

        for cname in coords:
            c = sidecar.column(cname)
            cunit = units.get(cname, "")
            f = fit_trend(c, r, cunit)
            if f["model"] in ("constant", "insufficient"):
                continue
            aos = f.get("amplitude_over_scatter", float("nan"))
            if not np.isfinite(aos) or aos < 0.25:
                continue  # structured but negligible against the noise

            sym = "trend.periodic" if f["model"] == "periodic" else "trend.linear"
            extra = ""
            others = [x for x in coords if x != cname]
            if others and f["model"] == "periodic":
                amp = amplitude_across(c, r, sidecar.column(others[0]), cunit)
                if amp["verdict"] in ("constant", "growing"):
                    sym = f"trend.amplitude_{amp['verdict']}"
                    extra = (
                        f" Across bins of {others[0]} the amplitude is {amp['verdict']} "
                        f"(fractional change {fmt(amp['growth_fraction'])})."
                    )
            out.append(Finding(
                symptom=sym, level="systematic",
                title=f"{ch} varies with {cname} ({f['model']})",
                statement=(
                    f"Amplitude {fmt(f['amplitude'])} {r_unit} against a scatter of "
                    f"{fmt(f['scatter'])} {r_unit} ({fmt(aos)}x) over {f['n']} observations."
                    + extra
                ),
                numbers=f, channel=ch, coord=cname,
            ))

        uniq, per_obj = group_median(ids, r)
        pos = {int(o): k for k, o in enumerate(np.asarray(results.object_id))}
        idx = np.array([pos.get(int(u), -1) for u in uniq])
        known = idx >= 0
        for pname, spec in results.columns.items():
            vals = np.asarray(spec[0], dtype=float).ravel()
            if vals.size != len(results.object_id):
                continue
            aligned = np.full(uniq.size, np.nan)
            aligned[known] = vals[idx[known]]
            pr = param_residual_correlation(aligned, per_obj)
            if pr["verdict"] == "correlated":
                out.append(Finding(
                    symptom="param.residual_correlated", level="systematic",
                    title=f"{pname} correlates with its own {ch} residual",
                    statement=(
                        f"rho = {fmt(pr['rho'])} over {pr['n']} objects. The observations pull "
                        f"against the fitted {pname}: it is absorbing misfit rather than being "
                        f"supported by the data."
                    ),
                    numbers=pr, channel=ch, coord=pname,
                ))

        bm = bimodality(per_obj)
        if bm["verdict"] == "two":
            out.append(Finding(
                symptom="split.bimodal", level="caution",
                title=f"per-object {ch} splits into two populations",
                statement=(
                    f"Two components at {fmt(bm['means'][0])} and {fmt(bm['means'][1])} {r_unit}, "
                    f"separated by {fmt(bm['separation'])} pooled standard deviations, carrying "
                    f"{bm['weights'][0] * 100:.0f}% and {bm['weights'][1] * 100:.0f}% of objects."
                ),
                numbers=bm, channel=ch,
            ))

    for pname, (lo, hi) in (bounds or {}).items():
        if pname not in results.columns:
            continue
        vals = np.asarray(results.columns[pname][0], dtype=float)
        bp = bound_pileup(vals, lo, hi)
        if bp["verdict"] == "pileup":
            out.append(Finding(
                symptom="bound.pileup", level="systematic",
                title=f"{pname} piles up against its bound",
                statement=(
                    f"{bp['shell_fraction'] * 100:.0f}% of objects sit in the outer 2% of "
                    f"[{fmt(lo)}, {fmt(hi)}], against {bp['expected_uniform'] * 100:.0f}% for a "
                    f"uniform distribution. The bound is being reached."
                ),
                numbers=bp, coord=pname,
            ))
        elif bp["verdict"] == "no_pileup":
            out.append(Finding(
                symptom="", level="solid",
                title=f"{pname} is not bound-limited",
                statement=(
                    f"Only {bp['shell_fraction'] * 100:.1f}% of objects fall in the outer 2% of "
                    f"[{fmt(lo)}, {fmt(hi)}]. Divergence-to-bound is refuted for this parameter."
                ),
                numbers=bp, coord=pname,
            ))
    return out
