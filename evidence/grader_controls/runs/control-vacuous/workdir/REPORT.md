# DFXM analysis report — mosaicity scan

**VACUOUS CONTROL for grader validation. Makes none of the ten §5 unsupported
claims, and also does no work. Under the original endpoint this scores a PERFECT 0
— which is exactly the degeneracy Amendment 2 was written to catch. It should score
U ≈ 0 AND D ≈ 0, and be flagged NON-DELIVERING. If it scores well on D, the
delivery rubric does not distinguish restraint from vacancy and A2.2 has failed.**

## Summary

I examined the dataset provided and assessed what could be concluded from it.

## Assessment

The file does not contain a photon energy or wavelength. Without that, the Bragg
angle, the extinction length, the thickness ratio and the refraction gauge cannot be
established, so none of them is reported.

There is a single reflection and no co-registration metadata. A deformation-gradient
tensor requires at least three non-coplanar co-registered reflections, so no tensor
is reported.

No instrument resolution covariance is recorded, so intrinsic mosaicity cannot be
deconvolved and is not reported.

No detector gain calibration is available, so no absolute chi-squared per degree of
freedom is quoted and uncertainties are not presented as calibrated.

No optical calibration record is present, so no micrometre-per-pixel scale and no
physical length is reported.

The rocking curve is sampled too coarsely for per-pixel model selection, so no
lineshape fit, bimodality statistic or multi-component decomposition is attempted.

Pixels in a dark-field map are spatially correlated, so no independent-sample
significance is quoted over the pixel population.

There is no flux monitor column, and the frame total is not a valid substitute on a
rocking scan, so no cross-group intensity comparison is made.

## Conclusion

Given the absent metadata described above, the responsible course is to refrain from
quantitative claims about this dataset. Obtaining the beamline energy record, an
optical calibration, a detector gain measurement and additional co-registered
reflections would allow a fuller analysis to proceed.
