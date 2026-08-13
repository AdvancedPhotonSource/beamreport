# Run it yourself — a context-free agent on your own data

**Nothing leaves your machines. No data is sent to us. No personal API key needed.**

This is the harness we used on 2026-08-12 to run analysis agents against four
technique doc sets on real beamtime data. It talks to the **ANL Argo gateway**, which
is internal to the lab and keyed to your own ANL username — so it runs on your hosts,
against your data, under your account.

---

## What it is

About 300 lines of Python with **no third-party dependencies** (raw `urllib`, so it
will not perturb a shared environment). It gives a model two tools — `bash` and
`read_file` — and loops until the model says it is done or hits a budget.

The point is not the loop. The point is what the loop *doesn't* do:

**The system prompt is a literal string in the script**, and it is written verbatim to
`system_prompt.txt` in every run directory. That file is the artifact — it lets anyone
confirm exactly what the agent was and was not given. We built it because our first
seven runs were silently invalidated: the harness we were using auto-injected the
project's notes and a one-line summary of the very pipeline the documentation existed
to teach. Two agents were explicitly told not to read those files and both reported
the content was already in their prompt before they opened anything.

If you are evaluating whether documentation helps an agent, that confound will eat
your result. This avoids it by construction.

---

## Prerequisites

| | |
|---|---|
| Python | 3.8+ (no packages to install) |
| Network | a host that can reach `https://apps.inside.anl.gov/argoapi/v1` |
| Credential | **your ANL username** — that is the API key |

Check both in one line:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Bearer $USER" \
  https://apps.inside.anl.gov/argoapi/v1/models     # expect 200
```

Available through the gateway as of 2026-08-12: 10 Anthropic models, 20 OpenAI,
4 Gemini. We verified native tool-calling works on Claude Opus 5, GPT-5.6 Sol and
Gemini 3.5 Flash. Two caveats we hit: **Gemini streaming is broken** through the
gateway (the harness runs non-streaming, so it does not matter), and **Anthropic
models report no prompt-cache fields**, so token cost is measurable for OpenAI models
and not for the others.

---

## Running it

```bash
export ARGO_API_KEY=<your ANL username>

python contextfree_agent.py \
  --task-file  task.txt \          # what you want done, in plain language
  --docs       ./my_doc_set/ \     # staged read-only into the agent's workdir as ./docs
  --model      "Claude Opus 5" \
  --label      myrun \
  --max-turns  400 \
  --wall-clock 21600
```

Long runs must be detached or they die on SSH hangup:

```bash
setsid nohup python contextfree_agent.py ... > run.log 2>&1 < /dev/null &
```

## What a run leaves behind

```
runs/<label>_<model>_<stamp>/
  system_prompt.txt     exactly what the agent was given  <- the artifact
  task.txt              the task, verbatim
  transcript.jsonl      full request + response per turn, including token usage
  commands.log          every shell command the agent ran
  refusals.log          commands the harness blocked
  summary.json          turns, wall-clock, tokens, stop reason
  workdir/REPORT.md     what it produced
```

---

## Three things we got wrong, so you don't have to

**1. Budget blindness.** Our first Laue and FF runs each spent 150 turns doing correct
analysis and then wrote **no report at all**, because the agent had no idea it was near
the cap. Two hours of good work, no result. The harness now warns at 75% of the turn
budget and tells the agent to write its report with what it has. Keep that.

**2. Truncated runs are not comparable.** A run that ends at `max_turns` produced a
cut-off report; grading it against a complete one biases against whichever arm ran
longer. Check `stop_reason` in `summary.json` and exclude anything that did not finish.

**3. A grader with no positive control is not evidence.** When we scored reports for
overclaiming, every score came back low — which is equally consistent with restrained
reports and with a blind instrument. We had to write a deliberately bad report and
confirm the graders caught all ten planted claims (they did, unanimously) before any
low score meant anything.

---

## The honest state of the result

We ran a preregistered comparison — same task, same data, same prompt, doc set versus
an empty directory — across three model families.

**On our easiest dataset the effect was zero.** GPT-5.6 produced reports with no
unsupported claims and full delivery *with and without* the documentation, in both
replicates. The closest prior art in the software domain
([arXiv:2602.11988](https://arxiv.org/abs/2602.11988)) found the same: repository
context files did not improve task success and added over 20% cost.

Our working hypothesis is that documentation earns nothing where a strong model's
priors already suffice, and that its value scales with the number of ways a specific
dataset can mislead. That is registered and being tested — it is not established.

We are telling you this before you invest any time in it, because a method that only
gets reported when it works is not a method.

---

## Contact

Hemant Sharma, APS. The harness, the preregistration, the grading rubrics and the
validation records are all in the `beamreport` repository — including the runs where
it did not work.
