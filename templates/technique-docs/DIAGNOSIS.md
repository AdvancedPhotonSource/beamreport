# <TECHNIQUE> diagnosis reference

Symptom → discriminating test → cause → lever. Read by `beamreport`; each entry attaches
to a symptom the generic diagnostics detect.

**Every entry carries a test that can come back the other way.** An entry that cannot
exonerate the cause it names does not belong here — it turns the report into a machine for
confirming whatever its author already believed.

Three entries is a working start. It grows the day someone works out what a strange plot
meant, not as a writing project.

---

## <Cause, named as a cause and not as a symptom>

symptom: trend.amplitude_constant

<!-- `symptom:` must be one of beamreport.SYMPTOMS. List them with:
     python -c "from beamreport import SYMPTOMS; print(*SYMPTOMS)"
     An entry keyed to a symptom nothing emits never fires, and reads as coverage. -->

**Test.** <The arithmetic separating this cause from the most plausible competing one.
State what the OTHER answer looks like and which entry it points to instead.>

**Cause.** <What it means when the test comes back this way.>

**Lever.** <The specific change that fixes it.>
