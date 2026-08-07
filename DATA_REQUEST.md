# Data request note (draft to forward)

Short, informal, no jargon from our side. Edit freely.

---

Hi,

Thanks for the interest. Here is what would be most useful to send, and why, so the first pass
gets us something real rather than a pretty page.

**Two datasets, one good and one problematic.** You already offered this and it is exactly
right. The diagnostic part of the report is built from contrast, so a dataset you argued about
is worth more to us than a second clean one. If there was a specific thing wrong with it,
please do not tell us what it was up front. We want to see whether the report finds it on its
own. Tell us afterwards.

**For each dataset:**

1. The reconstructed results, whatever form they come in. One row per thing you recovered.
2. Scan and sample parameters, as you mentioned.
3. **The residuals, if your pipeline keeps them.** This is the one that matters most, and it is
   the one most pipelines do not have. What we need is the per-observation difference between
   your model and your data, signed, before it gets squared and summed into a chi-squared,
   along with the coordinates each observation was taken at. If your fitting code computes this
   and then discards it, that is completely normal and it is a small change to persist it. If
   you are not sure, point us at the fitting routine and we will look.

Without item 3 we can still produce a report describing what was measured and how the results
distribute. With it, we can produce one that says which systematics are present and what to
change. The second is the part you were interested in.

**One more thing, and it costs about ten minutes:**

How do you tell, during a run, whether it is going well? Not the formal quality metric, the
practical version. The numbers someone glances at to decide whether to keep going or stop and
fix something, and roughly what range is normal for which kind of measurement.

Almost nobody has this written down, everybody knows it, and it turns out to be one of the more
useful things in the whole system. If it varies by measurement type, that variation is the
useful part, so please do not collapse it into one number.

**Format:** whatever is natural for you. We write a small adapter on our side, so please do not
reshape anything to suit us. If you want to see what the adapter has to produce before you
send, the spec is short and we can share it.

Thanks,
Hemant

---

## Internal notes (do not send)

- If they ask how much work is on their side: 50 to 100 lines of adapter, one afternoon,
  assuming residuals exist. If residuals need to be persisted, add a dozen lines in their fit.
- Do not accept "we have chi-squared per fit" as item 3. That is the information already
  destroyed. Ask to see the fitting routine.
- The good/problematic pair is what makes gates G2 and G3 reachable on the first pass. If they
  send two clean datasets, say so plainly and ask again rather than proceeding.
- Withholding the known defect is what makes G2 a real test rather than a demo. If they have
  already told us, note it and treat G2 as weakened evidence.
- Their healthy-ranges answer is the runbook table. It is free knowledge extraction and it is
  also the seam to the during-run work later.
