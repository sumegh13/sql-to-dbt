"""Build a self-contained dashboard from a project's results. Usage: dashboard.py [--project NAME]
Writes dashboard.html for the corpus, projects/<name>/dashboard.html for a user project."""
import argparse
import json
from pathlib import Path

from harness import project as projects

ap = argparse.ArgumentParser()
ap.add_argument("--project", default="corpus")
proj = projects.load(ap.parse_args().project)
out_file = Path("dashboard.html") if proj.name == "corpus" else proj.results.parent / "dashboard.html"

rows = []
for f in sorted(proj.results.glob("*.json")):
    r = json.loads(f.read_text())
    r["legacy_sql"] = (proj.procs / f.stem / "proc.sql").read_text()
    meta = json.loads((proj.procs / f.stem / "meta.json").read_text())
    # corpus procs are named by their folder; user projects by the real procedure name
    r["name"] = f.stem if proj.name == "corpus" else meta["proc"]
    r["retries"] = sum(1 for h in r.get("history", [])[:-1] if h.get("status") != "not_filterable")
    rows.append(r)
data = json.dumps(rows, default=str).replace("</", "<\\/")

HTML = """<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>SQL to dbt Migration</title>
<style>
:root{--bg:#fafaf7;--fg:#1c1c1a;--mut:#6b6b66;--card:#fff;--line:#e4e3dc;--ok:#1a7f4b;--okbg:#e3f3ea;--warn:#b4540a;--warnbg:#fbeadb;--code:#f3f2ec}
@media(prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe4;--mut:#9a9990;--card:#1d1d1b;--line:#2f2f2b;--ok:#4cc38a;--okbg:#17301f;--warn:#f0a35e;--warnbg:#3a2615;--code:#242421}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:1000px;margin:0 auto;padding:32px 16px}h1,.human p{overflow-wrap:anywhere}
h1{font-size:2rem;margin:0 0 4px}h1 b{color:var(--ok)}.sub{color:var(--mut);margin:0 0 20px}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line);margin-bottom:8px}
.bar i{display:block}.legend{display:flex;gap:16px;color:var(--mut);font-size:13px;margin-bottom:24px;flex-wrap:wrap}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:24px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.stat b{font-size:1.5rem;display:block}.stat span{color:var(--mut);font-size:13px}
.human{background:var(--warnbg);border:1px solid var(--warn);border-radius:10px;padding:4px 16px 12px;margin-bottom:24px}.human h2{font-size:1rem;color:var(--warn)}
.human p{margin:6px 0}
.filters{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
button{font:inherit;border:1px solid var(--line);background:var(--card);color:var(--fg);padding:4px 12px;border-radius:16px;cursor:pointer}button.on{background:var(--fg);color:var(--bg)}
details{background:var(--card);border:1px solid var(--line);border-radius:8px;margin-bottom:6px}
summary{padding:8px 12px;overflow-wrap:anywhere;cursor:pointer;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.tag{font-size:12px;padding:1px 8px;border-radius:10px;background:var(--code);color:var(--mut)}
.pill{font-size:12px;font-weight:600;padding:1px 9px;border-radius:10px}.v{background:var(--okbg);color:var(--ok)}.h{background:var(--warnbg);color:var(--warn)}
.body{padding:0 12px 12px;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px}.body>div{min-width:0}@media(max-width:700px){.body{grid-template-columns:minmax(0,1fr)}}
pre{background:var(--code);padding:10px;border-radius:6px;overflow:auto;font-size:12px;max-height:340px;margin:4px 0}h4{margin:8px 0 0;font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.sp{flex:1}.mut{color:var(--mut);font-size:13px}
</style><main><div id=app></div></main><script>
const R=%DATA%;const ok=R.filter(r=>r.status=='verified'),hu=R.filter(r=>r.status!='verified');
const diffs=['easy','medium','hard'].filter(d=>R.some(r=>r.difficulty==d));let f='all';
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
const pct=n=>(100*n/R.length)+'%';
const CAT={parameter_changes_grain:'Parameters change aggregation',output_parameters:'OUTPUT parameters',multiple_result_sets:'Multiple result sets',no_output:'No output',no_param_values:'No test parameter values',calls_other_proc:'Calls another proc',harness_error:'Harness error',dynamic_sql:'Dynamic SQL',nondeterministic:'Nondeterministic',mutates_source:'Mutates source tables',external_side_effect:'External side effect',unresolved_diff:'Unresolved diff',no_translation:'No translation'};
function row(r){const v=r.status=='verified';return `<details><summary><span class="pill ${v?'v':'h'}">${v?'verified':CAT[r.reason_category]||'needs human'}</span><b>${esc(r.name)}</b><span class=sp></span>${r.param_mode=='vars'?'<span class=tag>dbt vars</span>':r.param_filter?'<span class=tag>param filter</span>':''}${r.tags.map(t=>`<span class=tag>${esc(t)}</span>`).join('')}<span class=mut>${[r.difficulty!='unknown'?esc(r.difficulty):'',...(v?[Object.keys(r.datasets||{}).length+' datasets',r.rows+' rows',r.retries?r.retries+' retr'+(r.retries>1?'ies':'y'):'first try']:[])].filter(Boolean).join(' · ')}</span></summary><div class=body>
${r.explanation?`<div style="grid-column:1/-1"><h4>What it does</h4><p style="margin:4px 0">${esc(r.explanation)}</p></div>`:''}
${v?'':`<div style="grid-column:1/-1"><b>Why:</b> ${esc(r.reason)}</div>`}
${r.proposal?`<div style="grid-column:1/-1"><h4>Agent proposal for review</h4><p style="margin:4px 0"><span class="pill ${r.proposal.verification.startsWith('not')?'h':'v'}">${esc(r.proposal.verification)}</span></p>
${['assumptions','questions','not_migrated'].filter(k=>r.proposal[k]).map(k=>`<h4>${{assumptions:'Assumptions',questions:'Questions for the reviewer',not_migrated:'Not migrated'}[k]}</h4><pre style="white-space:pre-wrap">${esc(r.proposal[k])}</pre>`).join('')}</div>`:''}
${r.history&&r.history.length>1?`<div style="grid-column:1/-1"><h4>Attempt history</h4>${r.history.map(h=>`<p class=mut style="margin:2px 0">#${h.attempt} ${esc(h.status)}${h.status=='match'?'':': '+esc(typeof h.detail=='string'?h.detail.slice(0,240):JSON.stringify(h.detail.issues).slice(0,240))}</p>`).join('')}</div>`:''}
<div><h4>Legacy T-SQL</h4><pre>${esc(r.legacy_sql)}</pre></div><div><h4>dbt model</h4><pre>${r.model_sql?esc(r.model_sql):'(none: not auto-migratable)'}</pre>${r.param_filter?`<h4>Parameter filter</h4><pre style="white-space:pre-wrap">${esc(r.param_filter)}</pre>`:''}</div></div></details>`}
function draw(){const list=R.filter(r=>f=='all'||(f=='verified'?r.status=='verified':f=='human'?r.status!='verified':r.difficulty==f));
document.getElementById('app').innerHTML=`<h1><b>${ok.length} of ${R.length}</b> procedures migrated, verified equivalent</h1>
<p class=sub>${hu.length} need a human. Each dbt model ran on the same 4 datasets as the original T-SQL proc (base, two random seeds, and an edge-case set), with every parameter set, and matched row by row on every run.</p>
<div class=bar><i style="width:${pct(ok.length)};background:var(--ok)"></i><i style="width:${pct(hu.length)};background:var(--warn)"></i></div>
<div class=legend><span>Verified ${ok.length}</span><span>Needs human ${hu.length}</span></div>
<div class=stats><div class=stat><b>${ok.reduce((a,r)=>a+r.rows,0)}</b><span>rows compared</span></div><div class=stat><b>${ok.filter(r=>!r.retries).length}</b><span>passed first try</span></div><div class=stat><b>${ok.filter(r=>r.retries).length}</b><span>fixed by retry</span></div><div class=stat><b>$${R.reduce((a,r)=>a+(r.cost_usd||0),0).toFixed(3)}</b><span>LLM cost, full run</span></div></div>
<div class=human><h2>Needs a human (${hu.length})</h2>${hu.map(r=>`<p><b>${esc(r.name)}</b>: ${esc(r.reason)}${r.proposal?` <span class=mut>Proposal ready: ${esc(r.proposal.verification)}.</span>`:''}</p>`).join('')}</div>
<div class=filters>${['all','verified','human',...diffs].map(x=>`<button class="${f==x?'on':''}" onclick="f='${x}';draw()">${x}</button>`).join('')}</div>${list.map(row).join('')}`}
draw();</script></html>"""
out_file.write_text(HTML.replace("%DATA%", data))
print(out_file, len(rows), "procs")
