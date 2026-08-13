#!/usr/bin/env python3
"""contextfree_agent.py — a minimal, auditable agent harness for doc-set evaluation.

WHY THIS EXISTS
---------------
Seven prior doc-set runs were dispatched through Claude Code. That harness
auto-injects the project's CLAUDE.md, its MEMORY.md index, and a skill listing
that summarises the very pipeline the doc set exists to teach. Two runs were
explicitly told not to read ~/.claude and both reported the context had already
been injected before they opened a file. The instruction was inert.

The confound is a property of that harness, not of the model. This script calls
the chat-completions endpoint directly, so the system prompt is exactly the bytes
written in SYSTEM_PROMPT below and nothing else is loaded. That string is written
verbatim to system_prompt.txt in every run directory: it is the artifact that
lets a reader confirm what the agent was and was not given.

WHAT IT DOES NOT CLAIM
----------------------
The model still carries its pretraining, which includes diffraction and HEDM.
What is removed is *this project's accumulated context*. Report it as "no
project-specific context", never as "no context".

Deliberately zero third-party dependencies: raw urllib, so it runs under any
python3 without touching a shared environment.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# Gateway
# --------------------------------------------------------------------------
DEFAULT_BASE = "https://apps.inside.anl.gov/argoapi/v1"
DEFAULT_MODEL = "Claude Opus 5"

# --------------------------------------------------------------------------
# The system prompt. THIS IS THE MEASUREMENT ARTIFACT.
#
# Keep it minimal and free of domain hints. It must not name the pipeline
# shape, the phases, or any convention the doc set is supposed to teach --
# that is precisely the leak that invalidated the earlier runs. It also does
# NOT say the run is a documentation test: evidence file section 8 records
# that telling a session it was testing docs plausibly made it hunt for gaps
# harder than an ordinary user would.
# --------------------------------------------------------------------------
SYSTEM_PROMPT = """You are an analysis agent working at a synchrotron X-ray facility.

You have two tools: `bash` runs a shell command, `read_file` reads a file from disk.
Use them to do real work -- inspect data, run code, and check your results.

Ground every quantitative statement in something you actually ran. State the file
and the command that produced each number, so another person could re-derive it.
If you cannot establish something, say so plainly rather than estimating.

Work until the task is done or until you hit something that genuinely blocks you.
If you are blocked, say exactly what blocked you and what would unblock it.

When you are finished, write your final report to the file REPORT.md in your
working directory, and then say DONE.
"""

# --------------------------------------------------------------------------
# Context-leak guard.
#
# The agent's shell runs on a real machine that may hold this project's
# accumulated context on disk. Nothing is injected, but the agent could still
# choose to go looking. These patterns are refused and every refusal logged.
# "It never tried" is itself a reportable result.
# --------------------------------------------------------------------------
LEAK_PATTERNS = [
    r"\.claude",
    r"CLAUDE\.md",
    r"MEMORY\.md",
    r"COMMANDS\.md",
    r"known-limits",
    r"\.config/anthropic",
]
_LEAK_RE = re.compile("|".join(LEAK_PATTERNS), re.IGNORECASE)

MAX_TOOL_OUTPUT = 30_000  # chars returned to the model per tool call

# Fraction of the turn budget after which the agent is told to write its report.
WARN_FRACTION = 0.75


# --------------------------------------------------------------------------
# Tool schemas (OpenAI-compatible function calling)
# --------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command and return its combined stdout and stderr. "
                "Runs in your working directory. Use it to inspect files, run "
                "python, and check results."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to run."},
                    "timeout": {
                        "type": "integer",
                        "description": "Seconds before the command is killed. Default 300.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from disk and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file."},
                },
                "required": ["path"],
            },
        },
    },
]


# --------------------------------------------------------------------------
# Transport
# --------------------------------------------------------------------------
class Gateway:
    def __init__(self, base: str, key: str, timeout: int = 600):
        self.base = base.rstrip("/")
        self.key = key
        self.timeout = timeout

    def chat(self, payload: dict, max_retries: int = 4) -> dict:
        body = json.dumps(payload).encode()
        last = None
        for attempt in range(max_retries):
            req = urllib.request.Request(
                f"{self.base}/chat/completions",
                data=body,
                headers={
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:600]
                last = f"HTTP {e.code}: {detail}"
                # 4xx other than 429 will not fix themselves
                if e.code not in (408, 429) and e.code < 500:
                    raise RuntimeError(last) from e
            except Exception as e:  # noqa: BLE001 - transport is intentionally broad
                last = f"{type(e).__name__}: {e}"
            sleep = 2 ** attempt * 3
            print(f"  [retry {attempt + 1}/{max_retries} in {sleep}s] {last}", flush=True)
            time.sleep(sleep)
        raise RuntimeError(f"gateway failed after {max_retries} attempts: {last}")


# --------------------------------------------------------------------------
# Tool execution
# --------------------------------------------------------------------------
def _truncate(text: str) -> str:
    if len(text) <= MAX_TOOL_OUTPUT:
        return text
    keep = MAX_TOOL_OUTPUT // 2
    return (
        text[:keep]
        + f"\n\n...[{len(text) - MAX_TOOL_OUTPUT} chars elided by the harness]...\n\n"
        + text[-keep:]
    )


class Runner:
    def __init__(self, workdir: Path, rundir: Path):
        self.workdir = workdir
        self.rundir = rundir
        self.cmdlog = (rundir / "commands.log").open("a")
        self.refusals = (rundir / "refusals.log").open("a")
        self.n_refused = 0
        self.n_commands = 0

    def close(self):
        self.cmdlog.close()
        self.refusals.close()

    def _refuse(self, kind: str, payload: str) -> str:
        self.n_refused += 1
        self.refusals.write(f"[{kind}] {payload}\n")
        self.refusals.flush()
        return (
            "REFUSED BY HARNESS: this command touches the operator's private "
            "assistant configuration, which is out of scope for this task. "
            "Nothing there is relevant to the analysis. Proceed without it."
        )

    def bash(self, command: str, timeout: int = 300) -> str:
        self.n_commands += 1
        self.cmdlog.write(f"$ {command}\n")
        self.cmdlog.flush()
        if _LEAK_RE.search(command):
            return self._refuse("bash", command)
        try:
            p = subprocess.run(
                command,
                shell=True,
                cwd=self.workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            out = (p.stdout or "") + (p.stderr or "")
            return _truncate(out.strip() or f"(no output; exit {p.returncode})")
        except subprocess.TimeoutExpired:
            return f"TIMEOUT: command exceeded {timeout}s and was killed."
        except Exception as e:  # noqa: BLE001
            return f"HARNESS ERROR running command: {type(e).__name__}: {e}"

    def read_file(self, path: str) -> str:
        self.n_commands += 1
        self.cmdlog.write(f"read {path}\n")
        self.cmdlog.flush()
        if _LEAK_RE.search(path):
            return self._refuse("read", path)
        try:
            p = (self.workdir / path).resolve() if not path.startswith("/") else Path(path)
            return _truncate(p.read_text(errors="replace"))
        except Exception as e:  # noqa: BLE001
            return f"ERROR reading {path}: {type(e).__name__}: {e}"

    def dispatch(self, name: str, args: dict) -> str:
        if name == "bash":
            return self.bash(args.get("command", ""), int(args.get("timeout", 300) or 300))
        if name == "read_file":
            return self.read_file(args.get("path", ""))
        return f"ERROR: unknown tool {name!r}"


# --------------------------------------------------------------------------
# Agent loop
# --------------------------------------------------------------------------
def run(
    task: str,
    model: str,
    base: str,
    key: str,
    rundir: Path,
    max_turns: int,
    max_tokens: int,
    wall_clock_s: int,
) -> dict:
    workdir = rundir / "workdir"
    workdir.mkdir(parents=True, exist_ok=True)

    # The artifact: exactly what the agent was given.
    (rundir / "system_prompt.txt").write_text(SYSTEM_PROMPT)
    (rundir / "task.txt").write_text(task)

    transcript = (rundir / "transcript.jsonl").open("a")
    runner = Runner(workdir, rundir)
    gw = Gateway(base, key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    started = time.time()
    warned = False
    stop_reason = "max_turns"
    usage_total = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "cached_prompt_tokens": 0,
        "uncached_prompt_tokens": 0,
        "cache_reported": False,
        "per_turn": [],
    }

    for turn in range(1, max_turns + 1):
        elapsed = time.time() - started
        if elapsed > wall_clock_s:
            stop_reason = "wall_clock"
            break

        payload = {
            "model": model,
            "messages": messages,
            "tools": TOOLS,
            "max_tokens": max_tokens,
        }
        print(f"\n--- turn {turn}/{max_turns}  ({elapsed:.0f}s elapsed) ---", flush=True)

        try:
            resp = gw.chat(payload)
        except Exception as e:  # noqa: BLE001
            stop_reason = f"gateway_error: {e}"
            transcript.write(json.dumps({"turn": turn, "error": str(e)}) + "\n")
            break

        transcript.write(
            json.dumps({"turn": turn, "request": payload, "response": resp}) + "\n"
        )
        transcript.flush()

        # Raw prompt_tokens is NOT cost: on gateways that cache, most of the
        # re-transmitted history is billed at the cached rate. Record both, plus
        # the raw usage object, so cost can be computed rather than guessed.
        # Measured 2026-08-12: GPT-5.6 Sol reports prompt_tokens_details.cached_tokens
        # (98.9% hit on a repeated prefix); Claude via Argo reports no cache fields
        # at all — absence here means unmeasurable, not uncached.
        u = resp.get("usage") or {}
        usage_total["prompt_tokens"] += u.get("prompt_tokens", 0) or 0
        usage_total["completion_tokens"] += u.get("completion_tokens", 0) or 0
        det = u.get("prompt_tokens_details") or {}
        usage_total["cached_prompt_tokens"] += det.get("cached_tokens", 0) or 0
        usage_total["uncached_prompt_tokens"] = (
            usage_total["prompt_tokens"] - usage_total["cached_prompt_tokens"]
        )
        usage_total["cache_reported"] = bool(det)
        usage_total["per_turn"].append(
            {
                "turn": turn,
                "prompt_tokens": u.get("prompt_tokens", 0) or 0,
                "cached_tokens": det.get("cached_tokens", 0) or 0,
                "completion_tokens": u.get("completion_tokens", 0) or 0,
            }
        )

        choice = resp["choices"][0]
        msg = choice["message"]
        finish = choice.get("finish_reason")
        text = (msg.get("content") or "").strip()
        if text:
            print(text[:2000], flush=True)

        tool_calls = msg.get("tool_calls") or []

        # Echo the assistant turn back verbatim (tool_calls included).
        messages.append(
            {
                "role": "assistant",
                "content": msg.get("content") or None,
                **({"tool_calls": tool_calls} if tool_calls else {}),
            }
        )

        if not tool_calls:
            if "DONE" in text.upper() or finish == "stop":
                stop_reason = "agent_done"
                break
            # No tools and not finished: nudge once rather than spinning.
            messages.append(
                {
                    "role": "user",
                    "content": "Continue. Use your tools to make progress, or say DONE if finished.",
                }
            )
            continue

        for tc in tool_calls:
            fn = tc["function"]
            name = fn["name"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            preview = str(args.get("command") or args.get("path") or args)[:180]
            print(f"  -> {name}: {preview}", flush=True)
            result = runner.dispatch(name, args)
            messages.append(
                {"role": "tool", "tool_call_id": tc["id"], "content": result}
            )

        # Budget awareness. Without this the agent has no idea it is near the cap:
        # the 2026-08-12 Laue run spent all 150 turns doing good analysis and never
        # wrote its report, turning two hours of correct work into no result. The
        # Anthropic API exposes `task_budget` for exactly this; Argo's OpenAI-
        # compatible surface does not, so warn in-band. Appended after the tool
        # results so the tool_call/tool_result pairing is never broken.
        if not warned and turn >= int(WARN_FRACTION * max_turns):
            warned = True
            left = max_turns - turn
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"Budget notice: {left} of {max_turns} turns remain. "
                        "Write your report to REPORT.md now with what you have "
                        "established so far, stating plainly which questions you "
                        "did not get to. Do not start new lines of analysis."
                    ),
                }
            )
            print(f"  [harness] budget warning issued ({left} turns left)", flush=True)

    transcript.close()
    runner.close()

    summary = {
        "model": model,
        "base_url": base,
        "stop_reason": stop_reason,
        "turns_used": turn,
        "elapsed_s": round(time.time() - started, 1),
        "commands_run": runner.n_commands,
        "commands_refused_as_context_leak": runner.n_refused,
        "usage": usage_total,
        "report_written": (workdir / "REPORT.md").exists(),
    }
    (rundir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", s).strip("-").lower()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--task-file", required=True, help="File containing the task prompt.")
    ap.add_argument("--docs", required=True, help="Doc set directory to stage into the workdir as ./docs")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--base-url", default=os.environ.get("ARGO_BASE_URL", DEFAULT_BASE))
    ap.add_argument("--api-key", default=os.environ.get("ARGO_API_KEY", ""))
    ap.add_argument("--runs-root", default=str(Path(__file__).resolve().parent / "runs"))
    ap.add_argument("--label", default="run")
    ap.add_argument("--max-turns", type=int, default=120)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--wall-clock", type=int, default=7200, help="Seconds.")
    args = ap.parse_args()

    if not args.api_key:
        print("ERROR: no API key. Set ARGO_API_KEY or pass --api-key.", file=sys.stderr)
        return 2

    stamp = _dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    rundir = Path(args.runs_root) / f"{args.label}_{slug(args.model)}_{stamp}"
    rundir.mkdir(parents=True, exist_ok=True)
    workdir = rundir / "workdir"
    workdir.mkdir(exist_ok=True)

    # Stage the doc set read-only into the agent's workdir.
    docs_src = Path(args.docs).resolve()
    subprocess.run(["cp", "-r", str(docs_src), str(workdir / "docs")], check=True)

    task = Path(args.task_file).read_text()

    print(f"run dir : {rundir}")
    print(f"model   : {args.model}")
    print(f"gateway : {args.base_url}")
    print(f"docs    : {docs_src} -> {workdir / 'docs'}")
    print(f"guard   : refusing commands matching {LEAK_PATTERNS}")

    summary = run(
        task=task,
        model=args.model,
        base=args.base_url,
        key=args.api_key,
        rundir=rundir,
        max_turns=args.max_turns,
        max_tokens=args.max_tokens,
        wall_clock_s=args.wall_clock,
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(json.dumps(summary, indent=2))
    print(f"\nrun dir: {rundir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
