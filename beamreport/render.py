"""Page assembly: plates, stat tiles, findings, provenance strip, one self-contained file.

Everything here is generic. It embeds figures the caller rendered and lays out findings
the diagnostics computed; it draws nothing itself.

Output is a single HTML file with every image inlined as a data URI, so the page has no
external dependencies and survives being emailed, archived, or opened in five years.
The design tokens come from the report system these conventions grew out of, and the
page is theme-aware in both directions.
"""

from __future__ import annotations

import base64
import html
import string
from dataclasses import dataclass, field
from pathlib import Path

from .finding import Finding


class RenderError(ValueError):
    pass


@dataclass
class Plate:
    """A figure the caller rendered, plus what it shows.

    `spatial=True` asserts the axes are in the same units at the same scale. It is the
    caller's declaration, and it obliges them to have used an equal aspect: a stretched
    map misrepresents exactly the shape a reader is examining (SPEC 8.4).
    """

    path: str | Path
    title: str
    caption: str = ""
    spatial: bool = False
    aspect_equal: bool | None = None

    def validate(self) -> None:
        p = Path(self.path)
        if not p.exists():
            raise RenderError(f"plate image not found: {p}")
        if self.spatial and self.aspect_equal is False:
            raise RenderError(
                f"plate {self.title!r} is declared spatial but was drawn with a non-equal "
                f"aspect ratio (SPEC 8.4). A stretched map misrepresents grain shape and "
                f"elongation, which is what the reader is looking at."
            )

    def data_uri(self) -> str:
        p = Path(self.path)
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}
        ext = p.suffix.lower().lstrip(".")
        return f"data:{mime.get(ext, 'image/png')};base64," + base64.b64encode(p.read_bytes()).decode()


@dataclass
class Tile:
    value: str
    label: str


@dataclass
class Page:
    title: str
    subtitle: str = ""
    tiles: list[Tile] = field(default_factory=list)
    plates: list[Plate] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)
    coverage: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    methods: str = ""
    children: list = field(default_factory=list)  # (title, url, blurb) for an overview


def _e(s) -> str:
    return html.escape(str(s), quote=True)


# --------------------------------------------------------------------------- pieces


def _provenance(prov: dict) -> str:
    if not prov:
        raise RenderError(
            "no provenance supplied; a page with no provenance strip is refused (SPEC 8.3). "
            "A number that cannot be re-derived does not go on the page."
        )
    items = "".join(f"<span><b>{_e(k)}</b> {_e(v)}</span>" for k, v in prov.items() if v)
    return f'<div class="prov">{items}</div>'


def _tiles(tiles: list[Tile]) -> str:
    if not tiles:
        return ""
    cells = "".join(
        f'<div><div class="n">{_e(t.value)}</div><div class="l">{_e(t.label)}</div></div>'
        for t in tiles
    )
    return f'<div class="tiles">{cells}</div>'


def _finding(f: Finding) -> str:
    parts = [f'<div class="f f-{_e(f.level)}">',
             f'<div class="f-h">{_e(f.title)}</div>',
             f'<p class="f-s">{_e(f.statement)}</p>']
    if f.test:
        parts.append(f'<p class="f-t"><b>Test.</b> {_e(f.test)}</p>')
    if f.cause:
        parts.append(f'<p class="f-c"><b>Cause.</b> {_e(f.cause)}</p>')
    if f.lever:
        parts.append(f'<p class="f-l"><b>Lever.</b> {_e(f.lever)}</p>')
    elif f.symptom:
        parts.append(
            f'<p class="f-none">No diagnosis-reference entry for <code>{_e(f.symptom)}</code>. '
            f'The symptom is real and measured; what to do about it is not yet written down.</p>'
        )
    parts.append("</div>")
    return "".join(parts)


def _findings(findings: list[Finding], cov: dict) -> str:
    if not findings:
        return (
            '<div class="empty">No findings. Either the data is clean or no diagnostics '
            'could run. Check the provenance strip for which inputs were supplied.</div>'
        )
    body = "".join(_finding(f) for f in findings)
    note = ""
    if cov and cov.get("n_symptoms"):
        pct = round(100 * cov["fraction"])
        cls = "cov-ok" if pct >= 80 else "cov-low"
        extra = ""
        if cov["unexplained"]:
            extra = " Unexplained: " + ", ".join(f"<code>{_e(s)}</code>" for s in cov["unexplained"]) + "."
        note = (
            f'<div class="cov {cls}">Diagnosis reference explains {cov["n_explained"]} of '
            f'{cov["n_symptoms"]} detected symptoms ({pct}%) from {cov["n_entries"]} entries.'
            f'{extra}</div>'
        )
    return note + body


def _plates(plates: list[Plate]) -> str:
    out = []
    for p in plates:
        p.validate()
        cap = f'<figcaption>{_e(p.caption)}</figcaption>' if p.caption else ""
        out.append(
            f'<figure class="plate"><div class="plate-h">{_e(p.title)}</div>'
            f'<img src="{p.data_uri()}" alt="{_e(p.title)}">{cap}</figure>'
        )
    return "".join(out)


def _children(children: list) -> str:
    if not children:
        return ""
    cards = []
    for c in children:
        title, url, blurb = (list(c) + ["", ""])[:3]
        if not url:
            raise RenderError(
                f"child page {title!r} has no URL (SPEC 8.5). Publish children first, "
                f"collect their URLs, then build the overview."
            )
        cards.append(
            f'<a class="child" href="{_e(url)}"><div class="child-t">{_e(title)}</div>'
            f'<div class="child-b">{_e(blurb)}</div></a>'
        )
    return f'<section><h2>Measurements</h2><div class="kids">{"".join(cards)}</div></section>'


def _warnings(warns: list) -> str:
    if not warns:
        return ""
    items = "".join(f"<li>{_e(w)}</li>" for w in warns)
    return f'<div class="warn"><b>Contract warnings</b><ul>{items}</ul></div>'


# ------------------------------------------------------------------------ the shell

# string.Template, not str.format: CSS braces collide with format's syntax and the
# failure is a confusing KeyError deep in a stylesheet.
_TMPL = string.Template("""<title>$title</title>
<style>
:root{
 --paper:#f7f6f3;--raised:#fff;--sunk:#eeece7;--ink:#131619;--ink2:#3d4246;--muted:#6f6c66;
 --rule:#dcd9d2;--hair:#e6e3dc;--teal:#0e7c86;--teal-soft:#e2eeee;--copper:#ab6b2f;
 --copper-soft:#f5eade;--warnbg:#fdf6e6;
 --serif:ui-serif,Georgia,"Iowan Old Style","Times New Roman",serif;
 --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
 --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
 --paper:#15181a;--raised:#1c2023;--sunk:#101315;--ink:#e8e6e1;--ink2:#bcb9b2;--muted:#8d8981;
 --rule:#2f3437;--hair:#272c2f;--teal:#4bb8c1;--teal-soft:#173230;--copper:#dda06a;
 --copper-soft:#2d2318;--warnbg:#2a2415;}}
:root[data-theme=dark]{
 --paper:#15181a;--raised:#1c2023;--sunk:#101315;--ink:#e8e6e1;--ink2:#bcb9b2;--muted:#8d8981;
 --rule:#2f3437;--hair:#272c2f;--teal:#4bb8c1;--teal-soft:#173230;--copper:#dda06a;
 --copper-soft:#2d2318;--warnbg:#2a2415;}
:root[data-theme=light]{
 --paper:#f7f6f3;--raised:#fff;--sunk:#eeece7;--ink:#131619;--ink2:#3d4246;--muted:#6f6c66;
 --rule:#dcd9d2;--hair:#e6e3dc;--teal:#0e7c86;--teal-soft:#e2eeee;--copper:#ab6b2f;
 --copper-soft:#f5eade;--warnbg:#fdf6e6;}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
 font-size:16.5px;line-height:1.62;-webkit-font-smoothing:antialiased}
.shell{max-width:1080px;margin:0 auto;padding:0 26px 64px}
.prov{font-family:var(--mono);font-size:11.5px;line-height:1.9;color:var(--muted);
 border-top:2px solid var(--ink);border-bottom:1px solid var(--rule);padding:10px 0;
 display:flex;flex-wrap:wrap;gap:4px 28px;margin-top:46px}
.prov b{color:var(--ink2);font-weight:600}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(2rem,4.6vw,2.9rem);line-height:1.1;
 margin:30px 0 0;max-width:22ch;text-wrap:balance;letter-spacing:-.015em}
.sub{font-family:var(--serif);font-size:1.16rem;color:var(--ink2);max-width:60ch;margin:14px 0 0}
h2{font-family:var(--serif);font-weight:600;font-size:1.5rem;margin:0 0 14px;letter-spacing:-.01em}
section{padding:36px 0;border-bottom:1px solid var(--hair)}
section:last-of-type{border-bottom:0}
p{margin:0 0 14px;max-width:68ch;color:var(--ink2)}
code{font-family:var(--mono);font-size:.86em;background:var(--sunk);padding:.1em .34em;border-radius:2px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(146px,1fr));border:1px solid var(--rule);
 border-radius:2px;background:var(--raised);overflow:hidden;margin:26px 0 0}
.tiles div{padding:15px 16px;border-left:1px solid var(--hair)}
.tiles div:first-child{border-left:0}
.tiles .n{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:1.42rem;
 font-weight:600;letter-spacing:-.02em}
.tiles .l{font-size:12.5px;color:var(--muted);margin-top:4px;line-height:1.45}
.cov{font-family:var(--mono);font-size:12.4px;padding:10px 14px;border-radius:2px;margin:0 0 16px;
 border:1px solid var(--rule)}
.cov-ok{background:var(--teal-soft);border-color:var(--teal)}
.cov-low{background:var(--copper-soft);border-color:var(--copper)}
.f{border:1px solid var(--rule);border-left-width:3px;border-radius:0 2px 2px 0;
 background:var(--raised);padding:15px 18px;margin:0 0 12px}
.f-systematic{border-left-color:var(--copper)}
.f-solid{border-left-color:var(--teal)}
.f-caution{border-left-color:var(--muted)}
.f-h{font-weight:650;color:var(--ink);margin-bottom:6px}
.f p{font-size:14.6px;margin:0 0 8px;max-width:74ch}
.f p:last-child{margin-bottom:0}
.f-none{color:var(--muted);font-style:italic}
.empty{color:var(--muted);font-style:italic;padding:16px 0}
.warn{background:var(--warnbg);border-left:2px solid var(--copper);padding:12px 16px;margin:20px 0;
 border-radius:0 2px 2px 0;font-size:14.2px}
.warn ul{margin:8px 0 0;padding-left:20px}
.plate{margin:0 0 26px;border:1px solid var(--rule);border-radius:2px;background:#fff;overflow:hidden}
.plate-h{font-family:var(--mono);font-size:10.5px;font-weight:600;letter-spacing:.13em;
 text-transform:uppercase;color:#6f6c66;padding:11px 14px;border-bottom:1px solid #e6e3dc;background:#faf9f7}
.plate img{display:block;width:100%;height:auto}
.plate figcaption{font-size:13.2px;color:#6f6c66;padding:11px 14px;border-top:1px solid #e6e3dc;
 line-height:1.55;background:#faf9f7}
.kids{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:11px}
.child{display:block;border:1px solid var(--rule);border-radius:2px;background:var(--raised);
 padding:13px 15px;text-decoration:none;color:inherit;transition:border-color .13s}
.child:hover{border-color:var(--teal)}
.child-t{font-family:var(--serif);font-weight:600;font-size:1.02rem;color:var(--ink)}
.child-b{font-size:12.8px;color:var(--muted);margin-top:5px;line-height:1.5}
details{border-top:1px solid var(--hair);padding-top:16px;margin-top:8px}
summary{cursor:pointer;font-weight:640;font-size:14.6px}
details pre{font-family:var(--mono);font-size:12.4px;background:var(--sunk);padding:13px 15px;
 border-radius:2px;overflow-x:auto;white-space:pre-wrap}
a{color:var(--teal)}
a:focus-visible,.child:focus-visible{outline:2px solid var(--teal);outline-offset:3px}
@media (prefers-reduced-motion:reduce){.child{transition:none}}
</style>
<div class="shell">
$provenance
<h1>$title</h1>
$subtitle
$tiles
$warnings
$children
<section><h2>What the data says</h2>$findings</section>
$figures
$methods
</div>
""")


def render(page: Page) -> str:
    """Assemble one self-contained HTML page."""
    figures = ""
    if page.plates:
        figures = f'<section><h2>Figures</h2>{_plates(page.plates)}</section>'
    methods = ""
    if page.methods:
        methods = (
            f'<section><details><summary>Methods and caveats</summary>'
            f'<pre>{_e(page.methods)}</pre></details></section>'
        )
    return _TMPL.substitute(
        title=_e(page.title),
        provenance=_provenance(page.provenance),
        subtitle=f'<p class="sub">{_e(page.subtitle)}</p>' if page.subtitle else "",
        tiles=_tiles(page.tiles),
        warnings=_warnings(page.warnings),
        children=_children(page.children),
        findings=_findings(page.findings, page.coverage),
        figures=figures,
        methods=methods,
    )


def write(page: Page, out: str | Path) -> Path:
    p = Path(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(page))
    return p
