"""demo_proof/build_player.py — player DP self-contained (PROVED/MEASURED + certy + konsola + mapa).

Rozszerza player v1: dwie kolumny prawdy PROVED (certyfikaty z hashami+wersją solvera) / MEASURED
(liczby z raportów, RECON §C), strip konsoli/admisji (podpisane rekordy per akt), mapa granicy z
komórką 3d (inwersja), eksponat v1.0 (CfC-32/τ/102→779 ms; „317" TYLKO tu, konfiguracja jawna),
backdrop terenu (prezentacyjny; sieć widzi 64²). Klatki base64 inline (file:// offline). Zero
pomiarów. Wyjście: demo_proof/liquidsight_proof.html.

CLI: .venv/bin/python -m demo_proof.build_player
"""
from __future__ import annotations
import base64
import glob
import hashlib
import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO = os.path.join(_ROOT, "results", "demo_proof")
CERTS = os.path.join(_ROOT, "proofs", "certs")
OUT_HTML = os.path.join(_ROOT, "demo_proof", "liquidsight_proof.html")
ORDER = ["A1", "A2", "A3a", "A3b", "A4"]

ACTS = {
    "A1": {"title": "Act 1 — Command",
           "banner": "designation 67% / wrong-lock 10% — measured envelope (gate 85/8: frozen, unmet)",
           "source": "RAPORT_3B · RAPORT_3C_MVP §2",
           "note": "console → parser → signed admission → flight over terrain. shield APPLIED (transparent)."},
    "A2": {"title": "Act 2 — The link",
           "banner": "burst L5 = −4 pp vs scattered p0.5 = −36 pp — continuity is what matters",
           "source": "RAPORT_S3B4 (G2)",
           "note": "5 s contiguous gap: bbox freezes as ghost, age climbs, dwell still completes. shield APPLIED."},
    "A3a": {"title": "Act 3 — Hard rules (geofence)",
            "banner": "target beyond arena → REFUSE(GEOFENCE) at admission — proved (P2: never leaves 2.0 m)",
            "source": "RAPORT_3C_MVP §6 (25/25) · cert P2",
            "note": "admission refuses before launch; geometry, not perception."},
    "A3b": {"title": "Act 3 — Hard rules (stale)",
            "banner": "link killed at dwell → HOLD → REFUSE(STALE). accounting: 16/28 failures → abstention, 15/22 kept",
            "source": "RAPORT_3C_MVP §5",
            "note": "dead zone + dropout: age>2 s → HOLD → T_hold → REFUSE. blind guessing replaced by refusal."},
    "A4": {"title": "Act 4 — Correction",
           "banner": "unknown word → REFUSE(NO_MATCH) → operator maps alias (signed) → ALLOW → fly",
           "source": "cert P4 · A4_memory",
           "note": "alias resolved BEFORE parser; authorization always sees the canonical spec. no weight/threshold change."},
}
POOL = {"A1": "eval 46500–46599", "A2": "46500–46549", "A3a": "traps 47400–47449",
        "A3b": "46500–46549", "A4": "eval 46500–46599"}


def b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def mask_str(m, ms):
    return {"clean": "— (clean)", "bernoulli": f"Bernoulli p{m.get('p')} (seed {ms})",
            "burst": f"burst L{int(m.get('L',0))}s (seed {ms})",
            "geofence": "geofence (traps.py)"}.get(m["type"], m["type"])


def load_act(act, meta):
    d = os.path.join(DEMO, act)
    n = len(glob.glob(os.path.join(d, "3d", "f*.jpg")))
    frames = [{"d3": b64(os.path.join(d, "3d", f"f{i:03d}.jpg")),
               "c256": b64(os.path.join(d, "cam256", f"f{i:03d}.jpg")),
               "c64": b64(os.path.join(d, "cam64", f"f{i:03d}.jpg"))} for i in range(n)]
    trace = json.load(open(os.path.join(d, "trace.jsonl")))["trace"]
    spec = ACTS[act]
    adm = [{"phase": r.get("phase", "admit"), "cmd": r.get("command_raw", r.get("alias")),
            "decision": r.get("decision", "LEARN"), "reason": r.get("reason"),
            "sig": (r.get("sig", "")[:12])} for r in meta.get("admission", [])]
    return {"id": act, "title": spec["title"], "banner": spec["banner"], "source": spec["source"],
            "note": spec["note"], "command": meta["command"],
            "prov": {"pool": POOL[act], "seed": meta["seed"], "mask": mask_str(meta["mask"], meta.get("mask_seed")),
                     "outcome": meta["wynik"], "K": meta.get("K"), "A": meta.get("A"),
                     "attempts": meta.get("attempts", 1), "authz": meta.get("authz_verify", True)},
            "admission": adm, "frames": frames, "trace": trace}


def load_certs():
    out = {}
    for f in sorted(glob.glob(os.path.join(CERTS, "*.json"))):
        c = json.load(open(f))
        out[c["property"]] = {"verdict": c.get("verdict"),
                              "method": c.get("method", ""),
                              "hash": (c.get("model_sha256") or c.get("ckpt_sha256", ""))[:16],
                              "solver": c.get("z3_lib") or c.get("ibp", ""),
                              "scope": c.get("verdict_scope", "")}
    return out


def build():
    manifest = {m["act"]: m for m in json.load(open(os.path.join(DEMO, "manifest.json")))["episodes"]}
    acts = [load_act(a, manifest[a]) for a in ORDER if a in manifest]
    certs = load_certs()
    data = json.dumps({"acts": acts, "certs": certs}, separators=(",", ":"), ensure_ascii=False)
    html = HTML.replace("/*DATA*/", "const DATA=" + data + ";")
    with open(OUT_HTML, "w") as f:
        f.write(html)
    sha = hashlib.sha256(open(OUT_HTML, "rb").read()).hexdigest()
    print(f"ZAPIS -> {OUT_HTML}  ({os.path.getsize(OUT_HTML)/1e6:.1f} MB)  sha256={sha}")
    print(f"akty: {[a['id'] for a in acts]}  certy: {list(certs)}")
    return sha


HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LiquidSight — proved / measured / refused</title>
<style>
:root{--bg:#0b0e14;--panel:#12161f;--edge:#232a36;--txt:#e6e9ef;--dim:#8b93a3;
--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font-family:system-ui,Segoe UI,Roboto,sans-serif;font-size:14px}
.wrap{max-width:1180px;margin:0 auto;padding:14px}
h1{font-size:16px;margin:0 0 2px;letter-spacing:.3px}.sub{color:var(--dim);font-size:12px;margin-bottom:10px}
.banner{background:var(--panel);border:1px solid var(--edge);border-left:3px solid var(--blue);padding:9px 12px;border-radius:6px;font-size:13px;margin-bottom:10px;min-height:38px}
.banner b{color:#fff}.src{color:var(--dim);font-size:11px;font-family:var(--mono);margin-top:3px}
.grid{display:grid;grid-template-columns:1.7fr 1fr;gap:10px}.left{display:flex;flex-direction:column;gap:10px}
.view3d{border:1px solid var(--edge);border-radius:6px;overflow:hidden;position:relative;
background:linear-gradient(#1a2740 0%,#24405f 42%,#3a5a3f 42%,#243a28 100%)}
.view3d img{width:100%;display:block;mix-blend-mode:normal}
.tag{position:absolute;top:6px;left:8px;font-family:var(--mono);font-size:11px;color:var(--dim);background:rgba(0,0,0,.55);padding:2px 6px;border-radius:4px}
.terr{position:absolute;bottom:6px;right:8px;font-family:var(--mono);font-size:10px;color:var(--dim);background:rgba(0,0,0,.55);padding:2px 6px;border-radius:4px}
.cams{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.cam{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:6px;text-align:center}
.cam img{width:100%;image-rendering:pixelated;border-radius:3px}.cam .cap{font-family:var(--mono);font-size:11px;color:var(--dim);margin-top:4px}
.panel{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:12px;font-family:var(--mono)}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--edge);font-size:12.5px}
.row:last-child{border-bottom:none}.k{color:var(--dim)}.v{color:#fff;text-align:right}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.link-live{background:rgba(34,197,94,.15);color:var(--green)}.link-stale{background:rgba(234,179,8,.15);color:var(--yellow)}
.link-frozen{background:rgba(239,68,68,.15);color:var(--red)}.link-seeking{background:rgba(139,147,163,.15);color:var(--dim)}
.dec-ALLOW{color:var(--green)}.dec-HOLD{color:var(--yellow)}.dec-REFUSE{color:var(--red)}
.shieldbox{margin-top:10px;padding-top:8px;border-top:1px dashed var(--edge)}
.console{margin-top:10px;background:#0a0d13;border:1px solid var(--edge);border-radius:6px;padding:8px 10px;font-family:var(--mono);font-size:11.5px}
.console .cl{padding:2px 0}.cl .d-ALLOW{color:var(--green)}.cl .d-REFUSE{color:var(--red)}.cl .d-LEARN{color:var(--blue)}
.controls{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}
button{background:#1b2130;color:var(--txt);border:1px solid var(--edge);border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}
button:hover{background:#242c3d}button.on{border-color:var(--blue);color:#fff}
.scrub{flex:1;min-width:160px}input[type=range]{width:100%}
.prov{margin-top:10px;font-family:var(--mono);font-size:11px;color:var(--dim);background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:8px 10px}
.nav{display:flex;gap:6px;margin:10px 0;flex-wrap:wrap}.nav button{padding:5px 10px;font-size:12px}
.board{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:18px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.col h2{font-size:14px;margin:0 0 8px}.col.pr h2{color:var(--green)}.col.me h2{color:var(--blue)}
.card{border:1px solid var(--edge);border-radius:6px;padding:9px 11px;margin-bottom:8px;font-size:12.5px}
.card .t{font-weight:600}.card .m{color:var(--dim);font-size:11px;font-family:var(--mono);margin-top:3px}
.card .h{color:var(--dim);font-size:10.5px;font-family:var(--mono);margin-top:3px}
.vp{color:var(--green);font-weight:700}.vu{color:var(--yellow);font-weight:700}
.punch{border-left:3px solid var(--yellow);padding-left:9px;color:var(--txt);font-size:12px;margin-top:5px}
.exhibit{margin-top:14px;border-top:1px solid var(--edge);padding-top:12px}
.frozen{color:var(--green);font-weight:600;margin-top:10px}.road{color:var(--blue);font-family:var(--mono);font-size:12px;margin-top:8px}
.hidden{display:none}
</style></head><body><div class="wrap">
<h1>LiquidSight — we prove where a proof exists, measure where it does not, refuse where neither holds</h1>
<div class="sub">recordings of measured episodes · not new measurements · numbers from the frozen reports · proofs reproducible (python -m proofs.*)</div>
<div class="nav" id="nav"></div>
<div id="stage">
 <div class="banner"><span id="banner"></span><div class="src" id="src"></div></div>
 <div class="grid">
  <div class="left">
   <div class="view3d"><span class="tag">external 3D</span><img id="v3d"><span class="terr">terrain = third-person visualization; the network sees the 64² camera</span></div>
   <div class="cams">
    <div class="cam"><img id="v256"><div class="cap">grounder 256² · bbox+conf</div></div>
    <div class="cam"><img id="v64"><div class="cap">policy 64²</div></div>
   </div>
   <div class="controls"><button id="play">▶ play</button><button id="step">⟶ step</button>
    <span class="scrub"><input type="range" id="scrub" min="0" value="0"></span><button id="spd">1×</button></div>
   <div class="console" id="console"></div>
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
 <h1>two columns of truth</h1>
 <div class="cols">
  <div class="col pr"><h2>PROVED — certificates (reproducible)</h2><div id="proved"></div></div>
  <div class="col me"><h2>MEASURED — gates (from reports)</h2><div id="measured"></div></div>
 </div>
 <div class="exhibit">
  <h2>the map · liquid-net thread (measured, not promised)</h2>
  <div class="card"><span class="t">3d cell — target-channel micro-filter</span>: verdict NEGATIVE, Δ=−5.8 (CfC filter worse than no-filter; offline box-RMSE anti-correlates with success). <span class="m">RAPORT_3D §2</span></div>
  <div class="card"><span class="t">v1.0 exhibit — LiquidFlight (state-loop)</span>: CfC-32 flies under 500–1300 ms gaps; failure cliff ~102 ms → ~779 ms; τ≈35 ms; Δt no behavioral edge. <b>AutoNCP-20 (317 param)</b> is the state-loop config here — this is the only place "317" appears. <span class="m">paper/NUMBERS.md · LiquidFlight RD/C01 (config: setpoint→DSL-PID 48 Hz, obs-dropout OOD axis)</span></div>
  <div class="frozen">thresholds frozen before measurement · proofs signed with z3 5.0.0 / numpy-IBP</div>
  <div class="road">next: state continuity on public anti-UAV video (CT cores vs Kalman/GRU/Mamba)</div>
 </div>
</div>
</div>
<script>
/*DATA*/
let ai=0,fi=0,playing=false,spd=1,timer=null;const $=id=>document.getElementById(id);
const MEAS=[
 {t:"designation envelope",m:"67% success / 10% wrong-lock · gate 85/8 frozen, unmet",s:"RAPORT_3B · 3C_MVP §2"},
 {t:"executability ceiling",m:"GT-fed 100% — task is feasible for the executor",s:"RAPORT_3B §9"},
 {t:"broken-stream curve (G2)",m:"80 / 66 / 44 / 30 (p0/.25/.5/.75); burst L5 −4 pp vs scattered p0.5 −36 pp",s:"RAPORT_S3B4"},
 {t:"shield accounting (dropout)",m:"16 of 28 base failures → abstention; success kept 15/22",s:"RAPORT_3C_MVP §5"},
 {t:"geofence traps",m:"25/25 correct REFUSE(GEOFENCE)",s:"RAPORT_3C_MVP §6"},
 {t:"absent-object limit (honest)",m:"6/25 — open-vocab grounder hallucinates a box; perception is not proved",s:"RAPORT_3C_MVP §6"}];
const PUNCH="local robustness of the network is not provable by sound IBP at this width — that is why a proved automaton (P1, P2, P5) stands between the network and actuation.";
function certCard(k,c){let v=(c.verdict||"").toUpperCase();let cls=v.indexOf("PROV")>=0?"vp":"vu";
 let extra=(k==="P3")?('<div class="punch">'+PUNCH+'</div>'):'';
 return '<div class="card"><span class="t">'+k+'</span> · <span class="'+cls+'">'+v+'</span>'
 +'<div class="m">'+(c.method||'')+'</div><div class="h">solver '+(c.solver||'')+' · hash '+(c.hash||'')+'</div>'+extra+'</div>';}
function fillBoard(){let pr='';["P1","P2","P5","P4","A4_memory","P3"].forEach(k=>{if(DATA.certs[k])pr+=certCard(k,DATA.certs[k]);});
 $('proved').innerHTML=pr;$('measured').innerHTML=MEAS.map(x=>'<div class="card"><span class="t">'+x.t+'</span><div class="m">'+x.m+'</div><div class="h">'+x.s+'</div></div>').join('');}
function buildNav(){const n=$('nav');DATA.acts.forEach((a,i)=>{const b=document.createElement('button');b.textContent=a.title;
 b.onclick=()=>{showBoard(false);ai=i;fi=0;render();setActive();};n.appendChild(b);});
 const bb=document.createElement('button');bb.textContent='● proof board';bb.onclick=()=>showBoard(true);n.appendChild(bb);setActive();}
function setActive(){[...$('nav').children].forEach((b,i)=>b.classList.toggle('on',i===ai&&$('boardView').classList.contains('hidden')));}
function showBoard(on){$('boardView').classList.toggle('hidden',!on);$('stage').classList.toggle('hidden',on);pause();
 [...$('nav').children].forEach(b=>b.classList.remove('on'));if(on){$('nav').lastChild.classList.add('on');fillBoard();}else setActive();}
function render(){const a=DATA.acts[ai],fr=a.frames[fi]||a.frames[0],tr=a.trace[fi]||a.trace[a.trace.length-1];
 $('banner').innerHTML=a.banner.replace(/(\d+%|\d+\/\d+|−?\d+ ?pp|0\.\d+→?0?\.?\d*|85\/8|2\.0 m)/g,'<b>$1</b>');
 $('src').textContent='source: '+a.source;$('note').textContent=a.note;
 $('v3d').src=fr.d3;$('v256').src=fr.c256;$('v64').src=fr.c64;
 $('pCmd').textContent='"'+a.command+'"';$('pT').textContent=tr.t.toFixed(2)+' s / '+fi;
 const lk=tr.link||'seeking';$('pLink').textContent=lk.toUpperCase();$('pLink').className='pill link-'+lk;
 $('pAge').textContent=tr.age_s==null?'':'age '+(+tr.age_s).toFixed(1)+'s';
 $('pConf').textContent=tr.conf==null?'—':(+tr.conf).toFixed(3);
 $('pWL').textContent=tr.wrong_lock?'1  ⚠ other object':'0';$('pWL').style.color=tr.wrong_lock?'var(--red)':'var(--dim)';
 $('pState').textContent=tr.state;$('pRule').textContent=tr.rule||'—';
 $('pDec').textContent=tr.decision;$('pDec').className='v dec-'+tr.decision;$('pReason').textContent=tr.reason||'—';
 const c=a.admission.map(r=>'<div class="cl">▸ '+(r.phase)+': "'+(r.cmd||'')+'" → <span class="d-'+r.decision+'">'+r.decision+(r.reason?'('+r.reason+')':'')+'</span> <span style="color:var(--dim)">sig '+r.sig+'</span></div>').join('');
 $('console').innerHTML='<div style="color:var(--dim);margin-bottom:3px">CONSOLE · signed admission chain</div>'+(c||'—');
 const p=a.prov;$('prov').textContent='PROVENANCE  pool '+p.pool+' · seed '+p.seed+' · '+(p.K!=null?p.K+'/'+p.A+' · ':'')+'mask '+p.mask+' · outcome '+p.outcome+' · attempt '+p.attempts+'/3 · authz '+(p.authz?'ok':'FAIL');
 $('scrub').max=a.frames.length-1;$('scrub').value=fi;}
function tick(){const a=DATA.acts[ai];fi++;if(fi>=a.frames.length){fi=a.frames.length-1;pause();render();return;}render();}
function play(){if(playing)return;playing=true;$('play').textContent='❚❚ pause';$('play').classList.add('on');timer=setInterval(tick,Math.round(1000/12/spd));}
function pause(){playing=false;if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ play';$('play').classList.remove('on');}
$('play').onclick=()=>{if(playing)pause();else{if(fi>=DATA.acts[ai].frames.length-1)fi=0;play();}};
$('step').onclick=()=>{pause();fi=Math.min(fi+1,DATA.acts[ai].frames.length-1);render();};
$('scrub').oninput=e=>{pause();fi=+e.target.value;render();};
$('spd').onclick=()=>{spd=spd===1?2:spd===2?0.5:1;$('spd').textContent=spd+'×';if(playing){pause();play();}};
document.onkeydown=e=>{if(e.key===' '){e.preventDefault();$('play').click();}if(e.key==='ArrowRight')$('step').click();};
buildNav();render();
</script></body></html>"""


if __name__ == "__main__":
    build()
