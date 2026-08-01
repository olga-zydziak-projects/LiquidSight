"""demo/build_player.py — składa self-contained player HTML z nagranych klatek + trace.

Klatki (JPEG) i trace osadzone inline (base64 / JS) — file:// double-click działa offline
(przeglądarki blokują fetch() lokalnych plików). Zero pomiarów; liczby na ekranie z DEMO.md
(źródła w podpisach). Wyjście: demo/liquidsight_demo.html.

CLI: .venv/bin/python -m demo.build_player
"""
from __future__ import annotations
import base64
import glob
import hashlib
import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO = os.path.join(_ROOT, "results", "demo")
OUT_HTML = os.path.join(_ROOT, "demo", "liquidsight_demo.html")

# opisy aktów (EN) — treść i liczby z DEMO.md (frozen), każda liczba z odsyłaczem do raportu
ACTS = {
    "act1": {"title": "Act 1 — The language",
             "banner": "designation 67% / wrong-lock 10% — measured envelope "
                       "(pre-registered gate 85/8: frozen, unmet, reported)",
             "source": "RAPORT_3B, RAPORT_3C_MVP §2",
             "note": "clean approach, shield transparent (shadow)."},
    "act2": {"title": "Act 2 — The distractors",
             "banner": "attention↔target IoU 0.32 → 0.10 as distractors grow (K3→K8)",
             "source": "RAPORT_BASELINE_GRU (saliency, F3_GATE §6 W3)",
             "note": "toggle saliency: input-gradient of the goal-conditioned policy."},
    "act3": {"title": "Act 3 — Broken link",
             "banner": "burst L5 = −4 pp vs scattered p0.5 = −36 pp — continuity is what matters",
             "source": "RAPORT_S3B4 (G2)",
             "note": "5 s contiguous gap: bbox freezes as a ghost, age climbs, dwell still completes."},
    "act4a": {"title": "Act 4 — Refusal (a) geofence",
              "banner": "target beyond arena → REFUSE(GEOFENCE) before launch",
              "source": "RAPORT_3C_MVP §6 (S2: 25/25)",
              "note": "R-C checks target position at k=0, independent of perception."},
    "act4b": {"title": "Act 4 — Refusal (b) stale-at-dwell",
              "banner": "shield accounting (dropout leg): 16 of 28 base failures → safe abstention; "
                        "success preserved 15/22. uncertainty belongs to the shield",
              "source": "RAPORT_3C_MVP §5",
              "note": "link killed in the dead zone → age>2 s → HOLD → T_hold → REFUSE(STALE)."},
}
ORDER = ["act1", "act2", "act3", "act4a", "act4b"]


def b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def load_act(act, meta):
    d = os.path.join(DEMO, act)
    n = len(glob.glob(os.path.join(d, "3d", "f*.jpg")))
    frames = []
    has_sal = os.path.isdir(os.path.join(d, "saliency"))
    for i in range(n):
        fn = f"f{i:03d}.jpg"
        fr = {"d3": b64(os.path.join(d, "3d", fn)),
              "c256": b64(os.path.join(d, "cam256", fn)),
              "c64": b64(os.path.join(d, "cam64", fn))}
        if has_sal and os.path.exists(os.path.join(d, "saliency", fn)):
            fr["sal"] = b64(os.path.join(d, "saliency", fn))
        frames.append(fr)
    trace = json.load(open(os.path.join(d, "trace.jsonl")))["trace"]
    spec = ACTS[act]
    return {"id": act, "title": spec["title"], "banner": spec["banner"],
            "source": spec["source"], "note": spec["note"],
            "command": meta["command"], "hasSaliency": has_sal,
            "prov": {"pool": prov_pool(meta), "seed": meta["seed"],
                     "mask": mask_str(meta), "outcome": meta["wynik"],
                     "K": meta["K"], "A": meta["A"]},
            "frames": frames, "trace": trace}


def prov_pool(meta):
    a = meta["act"]
    return {"act1": "eval 46500–46599", "act2": "eval 46500–46599", "act3": "46500–46549",
            "act4a": "traps 47400–47449", "act4b": "46500–46549"}[a]


def mask_str(meta):
    m = meta["mask"]
    if m["type"] == "clean":
        return "— (clean)"
    if m["type"] == "bernoulli":
        return f"Bernoulli p{m['p']} (seed {meta['mask_seed']})"
    if m["type"] == "burst":
        return f"burst L{int(m['L'])}s (seed {meta['mask_seed']})"
    if m["type"] == "geofence":
        return "geofence (traps.py)"
    return m["type"]


def build():
    manifest = {m["act"]: m for m in json.load(open(os.path.join(DEMO, "manifest.json")))["episodes"]}
    acts = [load_act(a, manifest[a]) for a in ORDER if a in manifest]
    data_js = json.dumps({"acts": acts}, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("/*DATA*/", "const DATA=" + data_js + ";")
    with open(OUT_HTML, "w") as f:
        f.write(html)
    sz = os.path.getsize(OUT_HTML)
    sha = hashlib.sha256(open(OUT_HTML, "rb").read()).hexdigest()
    print(f"ZAPIS -> {OUT_HTML}  ({sz/1e6:.1f} MB)  sha256={sha}")
    return sha, sz


HTML_TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LiquidSight — 4-act demo</title>
<style>
:root{--bg:#0b0e14;--panel:#12161f;--edge:#232a36;--txt:#e6e9ef;--dim:#8b93a3;
--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);
font-family:system-ui,Segoe UI,Roboto,sans-serif;font-size:14px}
.wrap{max-width:1180px;margin:0 auto;padding:14px}
h1{font-size:16px;margin:0 0 2px;letter-spacing:.3px}
.sub{color:var(--dim);font-size:12px;margin-bottom:10px}
.banner{background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--blue);
padding:9px 12px;border-radius:6px;font-size:13px;margin-bottom:10px;min-height:38px}
.banner b{color:#fff}.src{color:var(--dim);font-size:11px;font-family:var(--mono);margin-top:3px}
.grid{display:grid;grid-template-columns:1.7fr 1fr;gap:10px}
.left{display:flex;flex-direction:column;gap:10px}
.view3d{background:#000;border:1px solid var(--edge);border-radius:6px;overflow:hidden;position:relative}
.view3d img{width:100%;display:block}
.tag{position:absolute;top:6px;left:8px;font-family:var(--mono);font-size:11px;color:var(--dim);
background:rgba(0,0,0,.55);padding:2px 6px;border-radius:4px}
.cams{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cam{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:6px;text-align:center}
.cam img{width:100%;image-rendering:pixelated;border-radius:3px}
.cam .cap{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:4px}
.panel{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:12px;font-family:var(--mono)}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--edge);font-size:12.5px}
.row:last-child{border-bottom:none}.k{color:var(--dim)}.v{color:#fff;text-align:right}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.link-live{background:rgba(34,197,94,.15);color:var(--green)}
.link-stale{background:rgba(234,179,8,.15);color:var(--yellow)}
.link-frozen{background:rgba(239,68,68,.15);color:var(--red)}
.link-seeking{background:rgba(139,147,163,.15);color:var(--dim)}
.dec-ALLOW{color:var(--green)}.dec-HOLD{color:var(--yellow)}.dec-REFUSE{color:var(--red)}
.shieldbox{margin-top:10px;padding-top:8px;border-top:1px dashed var(--edge)}
.controls{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
button{background:#1b2130;color:var(--txt);border:1px solid var(--edge);border-radius:6px;
padding:6px 12px;cursor:pointer;font-size:13px}button:hover{background:#242c3d}
button.on{border-color:var(--blue);color:#fff}
.scrub{flex:1;min-width:160px}input[type=range]{width:100%}
.prov{margin-top:10px;font-family:var(--mono);font-size:11px;color:var(--dim);
background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:8px 10px}
.nav{display:flex;gap:6px;margin:10px 0;flex-wrap:wrap}
.nav button{padding:5px 10px;font-size:12px}
.board{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:18px}
.board table{width:100%;border-collapse:collapse;margin:10px 0}
.board td,.board th{border:1px solid var(--edge);padding:8px 10px;text-align:left;font-size:13px}
.board th{color:var(--dim);font-weight:600}
.frozen{color:var(--green);font-weight:600}.road{color:var(--blue);font-family:var(--mono);font-size:12px;margin-top:10px}
.hidden{display:none}
</style></head><body><div class="wrap">
<h1>LiquidSight — designation · distractors · broken link · refusal</h1>
<div class="sub">recordings of measured episodes · not new measurements · numbers on screen come from the reports</div>
<div class="nav" id="nav"></div>
<div id="stage">
 <div class="banner"><span id="banner"></span><div class="src" id="src"></div></div>
 <div class="grid">
  <div class="left">
   <div class="view3d"><span class="tag">external 3D</span><img id="v3d"></div>
   <div class="cams">
    <div class="cam"><img id="v256"><div class="cap">grounder 256² · bbox+conf</div></div>
    <div class="cam"><img id="v64"><div class="cap" id="cap64">policy 64²</div></div>
   </div>
   <div class="controls">
    <button id="play">▶ play</button><button id="step">⟶ step</button>
    <span class="scrub"><input type="range" id="scrub" min="0" value="0"></span>
    <button id="spd">1×</button>
    <button id="salBtn" class="hidden">saliency: off</button>
   </div>
  </div>
  <div>
   <div class="panel">
    <div class="row"><span class="k">COMMAND</span><span class="v" id="pCmd"></span></div>
    <div class="row"><span class="k">t / frame</span><span class="v" id="pT"></span></div>
    <div class="row"><span class="k">LINK</span><span class="v"><span id="pLink" class="pill"></span> <span id="pAge"></span></span></div>
    <div class="row"><span class="k">conf</span><span class="v" id="pConf"></span></div>
    <div class="row"><span class="k">WRONG-LOCK</span><span class="v" id="pWL"></span></div>
    <div class="shieldbox">
     <div class="row"><span class="k">SHIELD state</span><span class="v" id="pState"></span></div>
     <div class="row"><span class="k">rule</span><span class="v" id="pRule"></span></div>
     <div class="row"><span class="k">decision</span><span class="v" id="pDec"></span></div>
     <div class="row"><span class="k">reason</span><span class="v" id="pReason"></span></div>
    </div>
   </div>
   <div class="prov" id="prov"></div>
   <div class="sub" id="note" style="margin-top:8px"></div>
  </div>
 </div>
</div>
<div id="boardView" class="board hidden">
 <h1>4 acts · 4 gates · 4 numbers</h1>
 <table><thead><tr><th>act</th><th>gate</th><th>number</th><th>source</th></tr></thead><tbody>
 <tr><td>1 language</td><td>designation</td><td>67% / 10%</td><td>RAPORT_3B</td></tr>
 <tr><td>2 distractors</td><td>saliency vs K</td><td>IoU 0.32→0.10</td><td>RAPORT_BASELINE_GRU</td></tr>
 <tr><td>3 broken link</td><td>bridging</td><td>L5 −4 vs p0.5 −36 pp</td><td>RAPORT_S3B4</td></tr>
 <tr><td>4 refusal</td><td>shield</td><td>16/28 failures → abstention</td><td>RAPORT_3C_MVP</td></tr>
 </tbody></table>
 <div class="frozen">thresholds frozen before measurement</div>
 <div class="road">next: state continuity on public anti-UAV video (CT cores vs Kalman/GRU/Mamba)</div>
</div>
</div>
<script>
/*DATA*/
let ai=0,fi=0,playing=false,spd=1,sal=false,timer=null;
const $=id=>document.getElementById(id);
function buildNav(){const n=$('nav');DATA.acts.forEach((a,i)=>{const b=document.createElement('button');
b.textContent=a.title;b.onclick=()=>{showBoard(false);ai=i;fi=0;render();setActive();};n.appendChild(b);});
const bb=document.createElement('button');bb.textContent='● final board';bb.onclick=()=>showBoard(true);n.appendChild(bb);setActive();}
function setActive(){[...$('nav').children].forEach((b,i)=>b.classList.toggle('on',i===ai && $('boardView').classList.contains('hidden')));}
function showBoard(on){$('boardView').classList.toggle('hidden',!on);$('stage').classList.toggle('hidden',on);
pause();[...$('nav').children].forEach(b=>b.classList.remove('on'));if(on)$('nav').lastChild.classList.add('on');else setActive();}
function render(){const a=DATA.acts[ai],fr=a.frames[fi],tr=a.trace[fi]||a.trace[a.trace.length-1];
$('banner').innerHTML=a.banner.replace(/(\d+%|\d+\/\d+|−?\d+ ?pp|0\.\d+→?0?\.?\d*|85\/8)/g,'<b>$1</b>');
$('src').textContent='source: '+a.source;$('note').textContent=a.note;
$('v3d').src=fr.d3;$('v256').src=fr.c256;
$('salBtn').classList.toggle('hidden',!a.hasSaliency);
$('v64').src=(sal&&a.hasSaliency&&fr.sal)?fr.sal:fr.c64;
$('cap64').textContent=(sal&&a.hasSaliency)?'policy 64² · saliency (|∂setpoint/∂px|, top-2%)':'policy 64²';
$('pCmd').textContent='"'+a.command+'"';
$('pT').textContent=tr.t.toFixed(2)+' s / '+fi;
const lk=tr.link||'seeking';$('pLink').textContent=lk.toUpperCase();$('pLink').className='pill link-'+lk;
$('pAge').textContent=tr.age_s==null?'':'age '+tr.age_s.toFixed(1)+'s';
$('pConf').textContent=tr.conf==null?'—':tr.conf.toFixed(3);
$('pWL').textContent=tr.wrong_lock?'1  ⚠ other object':'0';
$('pWL').style.color=tr.wrong_lock?'var(--red)':'var(--dim)';
$('pState').textContent=tr.state+(tr.shadow?'  (shadow)':'');
$('pRule').textContent=tr.rule||'—';
$('pDec').textContent=tr.decision;$('pDec').className='v dec-'+tr.decision;
$('pReason').textContent=tr.reason||'—';
const p=a.prov;$('prov').textContent='PROVENANCE  pool '+p.pool+' · seed '+p.seed+' · '+p.K+'/'+p.A+
' · mask '+p.mask+' · outcome '+p.outcome;
$('scrub').max=a.frames.length-1;$('scrub').value=fi;}
function tick(){const a=DATA.acts[ai];fi++;if(fi>=a.frames.length){fi=a.frames.length-1;pause();render();return;}render();}
function play(){if(playing)return;playing=true;$('play').textContent='❚❚ pause';$('play').classList.add('on');
timer=setInterval(tick,Math.round(1000/12/spd));}
function pause(){playing=false;if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ play';$('play').classList.remove('on');}
$('play').onclick=()=>{if(playing)pause();else{if(fi>=DATA.acts[ai].frames.length-1)fi=0;play();}};
$('step').onclick=()=>{pause();const a=DATA.acts[ai];fi=Math.min(fi+1,a.frames.length-1);render();};
$('scrub').oninput=e=>{pause();fi=+e.target.value;render();};
$('spd').onclick=()=>{spd=spd===1?2:spd===2?0.5:1;$('spd').textContent=spd+'×';if(playing){pause();play();}};
$('salBtn').onclick=()=>{sal=!sal;$('salBtn').textContent='saliency: '+(sal?'on':'off');$('salBtn').classList.toggle('on',sal);render();};
document.onkeydown=e=>{if(e.key===' '){e.preventDefault();$('play').click();}if(e.key==='ArrowRight')$('step').click();};
buildNav();render();
</script></body></html>"""


if __name__ == "__main__":
    build()
