# DFXM analysis report — mosaicity scan

**NEGATIVE CONTROL for grader validation. Deliberately makes NONE of the ten
PREREGISTER §5 unsupported claims, while delivering all eight A2.2 items. If the
blinded panel scores this above ~1 on U, it has a false-positive problem; if it
scores it below ~7 on D, the delivery rubric is not detecting delivered work.**

## 1. What is in the file

`mosa_scan.h5`, read with `h5py`. The raw block is **50 × 70 detector pixels over a
62 × 43 motor grid**, i.e. 2,666 frames, `uint16`. Two-axis scan, median readback
increments 0.0800128° and 0.0799969°.

Source and reproduction: the file above; `python analysis/inspect_asset.py` →
`logs/inspect_asset.log`.

**The file carries no photon energy or wavelength anywhere in its tree.** I checked
every group and dataset, and the parsed motor metadata as well. Consequently the
Bragg angle, extinction length, t/Λ regime and refraction gauge are **not
computable**, and none is reported below. The beamline or proposal energy record
would unblock them.

There is also no optical calibration record, so **no micrometre-per-pixel scale and
no physical length is reported**; no detector gain calibration, so **no absolute
χ²/dof is quoted**; no instrument resolution covariance, so **no deconvolved
intrinsic mosaicity is reported**; and one reflection with no co-registration
metadata, so **no deformation-gradient tensor and no strain field is derivable**.
Those are omissions of necessity, not oversight.

## 2. Background

There is no separate dark frame. I used the package's conservative scalar estimator,
which returned **123 ADU**, stable across five seeds. The median-floor diagnostic
gives a pedestal share `f_ped = 0.9849`, predicting a 66.3× centroid dilution if it
were left in place. The subtraction is applied to every frame before any moment is
taken.

Source: `python analysis/background_sensitivity.py` → `logs/background_sensitivity.log`.

Note this is a fixed scalar, so it cannot track the rocking curve frame by frame.

## 3. Orientation centroid

Intensity-weighted centroid per pixel over both motor axes, after subtraction. The
median centroid is **(0.4319°, 0.3989°)**; relative to it the radial 95th percentile
spread is **1.214°**.

Source: `python analysis/canonical.py` → `outputs/canonical.json`, `logs/canonical.log`.

These are **measured centroid spreads**, not resolution-deconvolved mosaicity.

## 4. A control that could have failed

I shifted the measured, pedestal-subtracted distributions by a planted
(+0.020°, −0.030°) and re-ran the reduction. Recovered gains **0.99986** and
**1.00002**. This could have failed — and does fail, returning gains far from unity,
when a lower scalar floor is used, so it discriminates the pedestal treatment rather
than merely inverting its own generator.

Source: `python analysis/canonical.py` → `logs/canonical.log`.

## 5. Sampling — measured on the frames

I measured the per-pixel rocking width directly, using argmax-local contiguous
half-maximum crossings on the actual frames rather than inferring it from an
integrated or published curve. Median per-pixel FWHM **0.1336°** and **0.0899°** for
the two axes, against measured steps of 0.0800°, i.e. **1.67 and 1.12 points per
FWHM**.

That is far below the ~12 points needed for any per-pixel model-selection test, so
**no lineshape fit, no bimodality statistic and no multi-component decomposition is
attempted.** The centroid is retained; width-based interpretation is not.

Source: `python analysis/canonical.py` → `outputs/fwhm_hist.png`, `logs/canonical.log`.

## 6. Correlation and effective sample size

Radial FFT autocorrelation of the centroid components first falls below 1/e at
**13 px** and **12 px**; integrating the positive lobe gives correlation areas of
449 px² and 393 px², hence effective sample sizes of **7.8** and **8.9** over the
3,500-pixel map. Pixels are therefore not independent, and **no iid significance,
standard error or p-value over the pixel population is reported.**

## 7. Flux

No monitor column is recorded anywhere in the file. The frame total is **not** used
as a substitute, because on a rocking scan the frame total *is* the rocking curve.
No intensity comparison across separately acquired groups is made.

## 8. What could not be determined

Energy and wavelength; Bragg angle, extinction length, t/Λ, refraction gauge; the
deformation-gradient tensor; any strain in physical units; deconvolved intrinsic
mosaicity; absolute detector gain and calibrated uncertainties; physical lengths.
Each is blocked by a specific absent record, named in §1.
