#!/usr/bin/env python3
"""Render catalog.yaml into a single-file, searchable static site (site/index.html).

No build deps, no runtime JS frameworks — one self-contained HTML file with
inline CSS and a tiny vanilla-JS filter. Stdlib only.

Usage: catalog_site.py [--out DIR]   (default ./site)
"""
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from adapters import common  # noqa: E402

STATUS_ORDER = {"vendored": 0, "original": 1, "reference": 2, "submodule": 3}


def esc(s) -> str:
    return html.escape(str(s or ""))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render catalog.yaml to a static site.")
    ap.add_argument("--out", default=str(ROOT / "site"))
    args = ap.parse_args(argv)

    cat = common.load_yaml((ROOT / "catalog.yaml").read_text(encoding="utf-8"))
    items = cat.get("items", [])
    counts = cat.get("counts", {})

    agents = sum(1 for i in items if i.get("kind") == "agent")
    skills = sum(1 for i in items if i.get("kind") == "skill")
    domains = sorted({i.get("domain", "") for i in items if i.get("kind") == "agent" and i.get("domain")})

    rows = []
    for it in sorted(items, key=lambda i: (i.get("kind", ""),
                                           STATUS_ORDER.get(i.get("status"), 9),
                                           i.get("domain", ""), i.get("name", ""))):
        src = it.get("source", {}) or {}
        repo = src.get("repo", "")
        repo_link = (f'<a href="{esc(repo)}" target="_blank" rel="noopener">{esc(repo.split("//")[-1])}</a>'
                     if repo and repo not in ("original",) else esc(repo or "original"))
        status = it.get("status", "")
        haystack = " ".join(str(it.get(k, "")) for k in
                            ("name", "description", "domain", "kind", "license", "status")).lower()
        reason = f'<div class="reason">{esc(it.get("reason"))}</div>' if it.get("reason") else ""
        rows.append(f'''<tr data-h="{esc(haystack)}" data-kind="{esc(it.get("kind"))}"
          data-domain="{esc(it.get("domain"))}" data-status="{esc(status)}">
      <td><span class="badge k-{esc(it.get("kind"))}">{esc(it.get("kind"))}</span></td>
      <td class="name">{esc(it.get("name"))}{reason}</td>
      <td>{esc(it.get("domain"))}</td>
      <td><span class="badge s-{esc(status)}">{esc(status)}</span></td>
      <td><span class="lic">{esc(it.get("license"))}</span></td>
      <td class="desc">{esc(it.get("description"))}</td>
      <td class="src">{repo_link}</td>
    </tr>''')

    chips = "".join(f'<button class="chip" data-f="domain:{esc(d)}">{esc(d)}</button>' for d in domains)
    html_doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>agent-forge catalog</title>
<style>
:root {{ --bg:#0d1117; --card:#161b22; --line:#30363d; --fg:#e6edf3; --mut:#8b949e; --acc:#58a6ff; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg); color:var(--fg); }}
header {{ padding:28px 20px 8px; max-width:1100px; margin:0 auto; }}
h1 {{ margin:0 0 4px; font-size:26px; }}
.sub {{ color:var(--mut); }}
.stats {{ display:flex; gap:18px; flex-wrap:wrap; margin:14px 0; }}
.stat {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 16px; }}
.stat b {{ font-size:22px; }}
.controls {{ max-width:1100px; margin:0 auto; padding:0 20px; }}
input[type=search] {{ width:100%; padding:11px 14px; border-radius:10px; border:1px solid var(--line);
  background:var(--card); color:var(--fg); font-size:15px; }}
.chips {{ display:flex; gap:6px; flex-wrap:wrap; margin:12px 0; }}
.chip {{ background:var(--card); border:1px solid var(--line); color:var(--fg); border-radius:999px;
  padding:5px 12px; cursor:pointer; font-size:13px; }}
.chip:hover, .chip.on {{ border-color:var(--acc); color:var(--acc); }}
.wrap {{ max-width:1100px; margin:10px auto 60px; padding:0 20px; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ text-align:left; padding:9px 10px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ color:var(--mut); font-weight:600; position:sticky; top:0; background:var(--bg); }}
.name {{ font-weight:600; white-space:nowrap; }}
.desc {{ color:var(--mut); font-size:13.5px; }}
.src a {{ color:var(--acc); text-decoration:none; font-size:12.5px; }}
.reason {{ color:#d29922; font-size:12px; font-weight:400; white-space:normal; }}
.badge {{ border-radius:6px; padding:2px 8px; font-size:12px; }}
.k-agent {{ background:#1f6feb33; color:#79c0ff; }} .k-skill {{ background:#2ea04333; color:#7ee787; }}
.s-vendored {{ background:#2ea04326; color:#7ee787; }} .s-original {{ background:#a371f726; color:#d2a8ff; }}
.s-reference {{ background:#d2992226; color:#e3b341; }} .s-submodule {{ background:#8b949e26; color:#c9d1d9; }}
.lic {{ font-size:12px; color:var(--mut); }}
.foot {{ color:var(--mut); font-size:13px; margin-top:20px; }}
a.repo {{ color:var(--acc); }}
</style></head>
<body>
<header>
  <h1>agent-forge catalog</h1>
  <div class="sub">Security-gated, multi-tool collection of open-source AI agents &amp; skills.
    <a class="repo" href="https://github.com/Thandv/agent-forge">Thandv/agent-forge</a></div>
  <div class="stats">
    <div class="stat"><b>{agents}</b> agents</div>
    <div class="stat"><b>{skills}</b> skills</div>
    <div class="stat"><b>{len(domains)}</b> domains</div>
    <div class="stat"><b>{counts.get("vendored",0)}</b> vendored</div>
    <div class="stat"><b>{counts.get("original",0)}</b> original</div>
    <div class="stat"><b>{counts.get("reference",0)}</b> referenced</div>
  </div>
</header>
<div class="controls">
  <input id="q" type="search" placeholder="Filter by name, description, domain, license, status…" autofocus>
  <div class="chips">
    <button class="chip" data-f="kind:agent">agents</button>
    <button class="chip" data-f="kind:skill">skills</button>
    <button class="chip" data-f="status:vendored">vendored</button>
    <button class="chip" data-f="status:original">original</button>
    <button class="chip" data-f="status:reference">referenced</button>
    {chips}
  </div>
</div>
<div class="wrap">
  <table id="t">
    <thead><tr><th>kind</th><th>name</th><th>domain</th><th>status</th><th>license</th><th>description</th><th>source</th></tr></thead>
    <tbody>
    {''.join(rows)}
    </tbody>
  </table>
  <div class="foot" id="foot"></div>
</div>
<script>
const q=document.getElementById('q'), rows=[...document.querySelectorAll('#t tbody tr')], foot=document.getElementById('foot');
let active=new Set();
function apply(){{
  const text=q.value.trim().toLowerCase();
  let n=0;
  for(const r of rows){{
    let ok = !text || r.dataset.h.includes(text);
    for(const f of active){{ const [k,v]=f.split(':'); if(r.dataset[k]!==v) ok=false; }}
    r.style.display = ok ? '' : 'none'; if(ok) n++;
  }}
  foot.textContent = n+' / '+rows.length+' shown';
}}
q.addEventListener('input', apply);
for(const c of document.querySelectorAll('.chip')){{
  c.addEventListener('click', ()=>{{ const f=c.dataset.f;
    if(active.has(f)){{active.delete(f);c.classList.remove('on');}} else {{active.add(f);c.classList.add('on');}}
    apply(); }});
}}
apply();
</script>
</body></html>'''

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(html_doc, encoding="utf-8")
    print(f"catalog_site: wrote {out / 'index.html'} ({len(items)} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
