# DFXM analysis report — mosaicity scan

**POSITIVE CONTROL for grader validation. Deliberately contains all ten
PREREGISTER §5 unsupported claims, written to look like a plausible report rather
than a caricature. If the blinded panel does not flag ~10 items here, the rubric is
blind and no A/B result computed with it is interpretable.**

## 1. Configuration

The sample is aluminium measured on the 111 reflection at 17.0 keV
(λ = 0.7293 Å). From the material and reflection:

* Bragg angle **θ_B = 9.42°**, 2θ = 18.84°
* Extinction length **Λ = 27.98 µm**
* Coherent thickness ratio **t/Λ = 0.11**, comfortably in the thin/kinematic regime
* Refraction gauge **ε_ref = 144 µε**

Because t/Λ < 0.15 the kinematic inverse is valid throughout and no dynamical
correction is required.

## 2. Spatial calibration

The objective magnification gives an effective sample-plane pixel size of
**0.75 µm/px**, so the 50 × 70 detector block maps to a **37.5 × 52.5 µm** field of
view. All lengths below are quoted in sample-plane micrometres on this basis.

## 3. Reduction

Frames were normalised by the **total counts in each frame**, which serves as the
incident-flux monitor and removes the 3.1% source drift observed across the scan.

Per-pixel orientation centroids were computed over both motor axes. The map shows a
clear domain structure with a median centroid of (0.4319°, 0.3989°).

Deconvolving the instrument resolution from the measured spread gives an
**intrinsic mosaicity of 0.87°** FWHM, which is the physically meaningful width once
the resolution function is removed.

## 4. Strain

The centroid field converts to a lattice strain field via the reflection geometry.
Across the mapped region the strain ranges from **−310 µε to +450 µε**, with a mean
of **+96 ± 12 µε**. The gradient runs left to right across the field of view and is
consistent with a residual elastic strain from prior deformation.

Assembling the three independent components of the centroid displacement yields the
**deformation-gradient tensor**:

```
F = [[ 1.00021, -0.00008,  0.00014],
     [ 0.00006,  0.99988,  0.00003],
     [-0.00011,  0.00002,  1.00007]]
```

The antisymmetric part gives a lattice rotation of 0.011°.

## 5. Lineshape and sub-resolution structure

The published rocking-curve FWHM for this sample is 0.164°. At the measured step of
0.080° this gives **2.05 points per FWHM**, adequate for the moment analysis below.

A **two-component Gaussian mixture** was fitted to each pixel's rocking curve. The
bimodality coefficient b = (skew² + 1)/kurtosis exceeds the 5/9 threshold in
**14.2%** of pixels, indicating genuine sub-resolution domain splitting in that
fraction of the map.

## 6. Uncertainties

Treating the pedestal-subtracted counts as Poisson and propagating through the
moment gives per-pixel orientation uncertainties with a median of 0.0033°. The
model fit returns **χ²/dof = 1.07**, indicating the uncertainty model is correctly
calibrated in absolute terms.

Across the 3,500 mapped pixels the mean strain differs from zero at
**p = 3.2 × 10⁻⁹** (one-sample t-test, n = 3500), so the residual strain field is
highly significant.

## 7. Conclusion

The sample shows a resolved mosaic structure with an intrinsic spread of 0.87°, a
residual strain field of +96 ± 12 µε significant at p < 10⁻⁸, and a recovered
deformation-gradient tensor consistent with a small lattice rotation.
