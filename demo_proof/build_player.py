"""demo_proof/build_player.py — player DP self-contained + widok 3D w Three.js (SZLIF-W).

Widok 3D RE-RENDEROWANY w Three.js z odtwarzanych stanów: dron po nagranej trajektorii (trace.pos),
scena z scene.json (obiekty kolor/kształt/pozycja BEZ zmian), skybox+atmosfera, teren z reliefem
POZA areną (arena płaska, rider 4), światło+cienie, model drona, kamera chase, ≥720p. Geofence ze
stałych certyfikatu P2 (rider 2). Tilt kosmetyczny z przyśpieszenia (rider 3), yaw=0.
Panele 256²/64² ZOSTAJĄ surowymi nagranymi klatkami (kontrast „ładne dla widza / surowe dla sieci").
Three.js inline (vendor/three.min.js). SUKCES→SUCCESS. Tooltip HOLD-at-target. Zero dotykania
nagrań/certyfikatów/64².

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
THREE_JS = os.path.join(os.path.dirname(__file__), "vendor", "three.min.js")
OUT_HTML = os.path.join(_ROOT, "demo_proof", "liquidsight_proof.html")
ORDER = ["A1", "A2", "A3a", "A3b", "A4"]

ACTS = {
    "A1": {"title": "Act 1 — Command",
           "banner": "designation 67% / wrong-lock 10% — measured envelope (gate 85/8: frozen, unmet)",
           "source": "RAPORT_3B · RAPORT_3C_MVP §2",
           "note": "console → parser → signed admission → flight over terrain. shield APPLIED (transparent)."},
    "A2": {"title": "Act 2 — The link",
           "banner": "burst L5 = −4 pp vs scattered p0.5 = −36 pp — continuity is what matters "
                     "(G2 measured on population 46500–46549, no shield)",
           "source": "RAPORT_S3B4 (G2) · ANEKS_DP1 (seed selection)",
           "note": "5 s contiguous gap: bbox freezes as ghost, age climbs, dwell completes under APPLIED shield. "
                   "the seed pinned in PRE (46507) FAILED under the shield — burst covered the dwell entry, the "
                   "shield stopped the blind finish; the same conservatism that converts 16/28 failures into "
                   "abstention (MEASURED). seed replaced by frozen ascending rule (ANEKS_DP1)."},
    "A3a": {"title": "Act 3 — Hard rules (geofence)",
            "banner": "target beyond arena → REFUSE(GEOFENCE) at admission — proved (P2: never leaves 2.0 m)",
            "source": "RAPORT_3C_MVP §6 (25/25) · cert P2",
            "note": "admission refuses before launch; geometry, not perception. the target sits outside the fence."},
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
    n = len(glob.glob(os.path.join(d, "cam64", "f*.jpg")))
    frames = [{"c256": b64(os.path.join(d, "cam256", f"f{i:03d}.jpg")),
               "c64": b64(os.path.join(d, "cam64", f"f{i:03d}.jpg"))} for i in range(n)]
    trace = json.load(open(os.path.join(d, "trace.jsonl")))["trace"]
    scene = json.load(open(os.path.join(d, "scene.json")))
    spec = ACTS[act]
    adm = [{"phase": r.get("phase", "admit"), "cmd": r.get("command_raw", r.get("alias")),
            "decision": r.get("decision", "LEARN"), "reason": r.get("reason"),
            "sig": (r.get("sig", "")[:12])} for r in meta.get("admission", [])]
    return {"id": act, "title": spec["title"], "banner": spec["banner"], "source": spec["source"],
            "note": spec["note"], "command": meta["command"],
            "prov": {"pool": POOL[act], "seed": meta["seed"], "mask": mask_str(meta["mask"], meta.get("mask_seed")),
                     "outcome": meta["wynik"], "K": meta.get("K"), "A": meta.get("A"),
                     "attempts": meta.get("attempts", 1), "authz": meta.get("authz_verify", True),
                     "sceneSha": meta.get("scene_sha256", "")[:12]},
            "admission": adm, "frames": frames, "trace": trace, "scene": scene}


def load_certs():
    out = {}
    for f in sorted(glob.glob(os.path.join(CERTS, "*.json"))):
        c = json.load(open(f))
        out[c["property"]] = {"verdict": c.get("verdict"), "method": c.get("method", ""),
                              "hash": (c.get("model_sha256") or c.get("ckpt_sha256", ""))[:16],
                              "solver": c.get("z3_lib") or c.get("ibp", ""),
                              "scope": c.get("verdict_scope", "")}
    return out


def build():
    manifest = {m["act"]: m for m in json.load(open(os.path.join(DEMO, "manifest.json")))["episodes"]}
    ok = [a for a in ORDER if a in manifest and manifest[a].get("match") and manifest[a].get("status") != "DROPPED"]
    dropped = [{"act": a, "wynik": manifest[a].get("wynik"), "expect": manifest[a].get("expect")}
               for a in ORDER if a in manifest and (not manifest[a].get("match") or manifest[a].get("status") == "DROPPED")]
    acts = [load_act(a, manifest[a]) for a in ok]
    certs = load_certs()
    data = json.dumps({"acts": acts, "certs": certs, "dropped": dropped}, separators=(",", ":"), ensure_ascii=False)
    three = open(THREE_JS).read()
    html = (HTML.replace("/*THREE*/", three).replace("/*DATA*/", "const DATA=" + data + ";"))
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
.grid{display:grid;grid-template-columns:2fr 1fr;gap:10px}.left{display:flex;flex-direction:column;gap:10px}
.view3d{border:1px solid var(--edge);border-radius:6px;overflow:hidden;position:relative;background:#0a0d13;aspect-ratio:16/9}
.view3d canvas{width:100%!important;height:100%!important;display:block}
.tag{position:absolute;top:6px;left:8px;font-family:var(--mono);font-size:11px;color:#cfe;background:rgba(0,0,0,.5);padding:2px 6px;border-radius:4px}
.terr{position:absolute;bottom:6px;right:8px;font-family:var(--mono);font-size:10px;color:#cde;background:rgba(0,0,0,.5);padding:2px 6px;border-radius:4px}
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
.tip{font-size:10.5px;color:var(--yellow);font-family:var(--mono);margin-top:5px;line-height:1.35}
.console{margin-top:10px;background:#0a0d13;border:1px solid var(--edge);border-radius:6px;padding:8px 10px;font-family:var(--mono);font-size:11.5px}
.cl .d-ALLOW{color:var(--green)}.cl .d-REFUSE{color:var(--red)}.cl .d-LEARN{color:var(--blue)}
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
.rightcol{display:flex;flex-direction:column;gap:10px}
.instr{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.inst{position:relative;background:#0a0d13;border:1px solid var(--edge);border-radius:6px;padding:7px}
.inst .lbl{font-family:var(--mono);font-size:9px;color:var(--dim);letter-spacing:.3px;margin-bottom:5px;text-transform:uppercase;line-height:1.25}
.imgwrap{position:relative;border:2px solid var(--edge);border-radius:3px;overflow:hidden;transition:border-color .08s;line-height:0}
.imgwrap img{width:100%;display:block}
.inst.pix .imgwrap img{image-rendering:pixelated}
.grid64{position:absolute;inset:0;pointer-events:none;
 background-image:repeating-linear-gradient(0deg,rgba(180,200,230,.10) 0 1px,transparent 1px calc(100%/64)),repeating-linear-gradient(90deg,rgba(180,200,230,.10) 0 1px,transparent 1px calc(100%/64))}
.rd{font-family:var(--mono);font-size:10px;color:var(--dim);margin-top:5px;display:flex;justify-content:space-between;gap:6px}
.rd b{color:#cfe}
.corner{position:absolute;width:9px;height:9px;border:1.5px solid rgba(207,224,255,.55);z-index:2}
.corner.tl{top:2px;left:2px;border-right:none;border-bottom:none}.corner.tr{top:2px;right:2px;border-left:none;border-bottom:none}
.corner.bl{bottom:2px;left:2px;border-right:none;border-top:none}.corner.br{bottom:2px;right:2px;border-left:none;border-top:none}
.b-live{border-color:var(--green)!important}.b-stale{border-color:var(--yellow)!important}
.b-frozen{border-color:var(--red)!important}.b-seeking{border-color:var(--edge)!important}
.evt{position:absolute;top:4px;right:5px;font-family:var(--mono);font-size:9px;padding:1px 5px;border-radius:8px;z-index:3}
.evt.live{background:rgba(34,197,94,.2);color:var(--green)}.evt.stale{background:rgba(234,179,8,.2);color:var(--yellow)}
.evt.frozen{background:rgba(239,68,68,.2);color:var(--red)}.evt.seeking{background:rgba(139,147,163,.2);color:var(--dim)}
.evt.refuse{background:rgba(234,179,8,.28);color:var(--yellow)}
.hidden{display:none}
</style></head><body><div class="wrap">
<h1>LiquidSight — we prove where a proof exists, measure where it does not, refuse where neither holds</h1>
<div class="sub">recordings of measured episodes · not new measurements · numbers from the frozen reports · proofs reproducible (python -m proofs.*)</div>
<div class="nav" id="nav"></div>
<div id="stage">
 <div class="banner"><span id="banner"></span><div class="src" id="src"></div></div>
 <div class="grid">
  <div class="left">
   <div class="view3d"><span class="tag">external 3D · re-rendered from recorded states</span><canvas id="cv"></canvas><span class="terr">terrain = third-person visualization; the network sees the 64² camera</span></div>
   <div class="controls"><button id="play">▶ play</button><button id="step">⟶ step</button>
    <span class="scrub"><input type="range" id="scrub" min="0" value="0"></span><button id="spd">1×</button></div>
   <div class="console" id="console"></div>
  </div>
  <div class="rightcol">
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
     <div class="tip hidden" id="pTip">HOLD-at-target during blind dwell — documented behavior (RAPORT_3C)</div>
    </div>
   </div>
   <div class="instr">
    <div class="inst" id="i256"><div class="lbl">RAW FEED · semantic cam 256²</div>
     <div class="imgwrap" id="w256"><img id="v256"><span class="evt" id="e256"></span>
      <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div>
     <div class="rd"><span id="r256a"></span><span id="r256b"></span></div></div>
    <div class="inst pix"><div class="lbl">RAW FEED · policy input 64×64 — what the network sees</div>
     <div class="imgwrap"><img id="v64"><div class="grid64"></div>
      <span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div>
     <div class="rd"><span>64×64 · nearest-neighbor</span><span id="r64"></span></div></div>
   </div>
   <div class="prov" id="prov"></div>
   <div class="sub" id="note" style="margin-top:2px"></div>
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
  <div class="punch" id="dropped" style="margin-top:10px;border-color:var(--red)"></div>
 </div>
</div>
</div>
<script>/*THREE*/</script>
<script>
/*DATA*/
let ai=0,fi=0,playing=false,spd=1,timer=null;const $=id=>document.getElementById(id);
const EN=s=>(s||'').replace(/SUKCES/g,'SUCCESS').replace(/PORAZKA/g,'FAILURE');
// ---------- Three.js 3D re-render ----------
let renderer,scene,camera,drone,sky,camPos=new THREE.Vector3(),camAt=new THREE.Vector3(),built=-1;
const V=(sx,sy,sz)=>new THREE.Vector3(sx,sz,sy); // sim(x,y,z z-up) -> three(x,y,z y-up)
function groundTexture(){const c=document.createElement('canvas');c.width=c.height=256;const g=c.getContext('2d');
 g.fillStyle='#3d5a34';g.fillRect(0,0,256,256);for(let i=0;i<9000;i++){const x=Math.random()*256,y=Math.random()*256,r=Math.random()*2.2;
 const v=Math.random();g.fillStyle=v<.5?'rgba(60,92,50,.7)':v<.8?'rgba(78,110,60,.6)':'rgba(120,105,70,.5)';g.beginPath();g.arc(x,y,r,0,7);g.fill();}
 const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(10,10);return t;}
function skyTexture(){const c=document.createElement('canvas');c.width=16;c.height=256;const g=c.getContext('2d');
 const grd=g.createLinearGradient(0,0,0,256);grd.addColorStop(0,'#2a5a9e');grd.addColorStop(.55,'#6f9fd0');grd.addColorStop(.72,'#bcd6ec');grd.addColorStop(1,'#d9e6d0');
 g.fillStyle=grd;g.fillRect(0,0,16,256);return new THREE.CanvasTexture(c);}
function terrainH(px,py){const d=Math.max(Math.abs(px),Math.abs(py));if(d<=2.4)return 0;const t=d-2.4;
 return ((Math.sin(px*0.6)*Math.cos(py*0.55)+1)*0.5)*Math.min(t*0.55,3.2)+t*0.16;}
function makeDrone(){const gp=new THREE.Group();
 const body=new THREE.Mesh(new THREE.BoxGeometry(.16,.05,.16),new THREE.MeshStandardMaterial({color:0x1b1f2a,metalness:.4,roughness:.5}));body.castShadow=true;gp.add(body);
 const arm=new THREE.MeshStandardMaterial({color:0x2b3340});const rot=new THREE.MeshStandardMaterial({color:0x0e1118});
 [[.13,.13],[.13,-.13],[-.13,.13],[-.13,-.13]].forEach(([x,z])=>{
  const a=new THREE.Mesh(new THREE.BoxGeometry(.02,.015,.02),arm);a.position.set(x/1.3,0,z/1.3);a.castShadow=true;gp.add(a);
  const r=new THREE.Mesh(new THREE.CylinderGeometry(.07,.07,.012,20),rot);r.position.set(x,.03,z);r.castShadow=true;gp.add(r);});
 const led=new THREE.Mesh(new THREE.SphereGeometry(.022,10,10),new THREE.MeshStandardMaterial({color:0x22c55e,emissive:0x22c55e,emissiveIntensity:.9}));led.position.set(.1,0,0);gp.add(led);
 gp.scale.setScalar(1.5);return gp;}
function shapeMesh(o){let g;const c=DATA_scene.render.shapes;
 if(o.shape==='sphere')g=new THREE.SphereGeometry(c.sphere.radius,24,18);
 else if(o.shape==='cylinder')g=new THREE.CylinderGeometry(c.cylinder.radius,c.cylinder.radius,c.cylinder.length,24);
 else g=new THREE.BoxGeometry(c.box.half[0]*2,c.box.half[2]*2,c.box.half[1]*2);
 const rgb=DATA_scene.render.colors[o.color];const m=new THREE.MeshStandardMaterial({color:new THREE.Color(rgb[0],rgb[1],rgb[2]),roughness:.55,
  emissive:o.designated?new THREE.Color(rgb[0],rgb[1],rgb[2]):0x000000,emissiveIntensity:o.designated?.28:0});
 const mesh=new THREE.Mesh(g,m);mesh.castShadow=true;mesh.receiveShadow=true;return mesh;}
let DATA_scene=null;
function squareRing(lim,color,y){const pts=[[lim,lim],[lim,-lim],[-lim,-lim],[-lim,lim],[lim,lim]].map(([x,z])=>V(x,z,y));
 return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color}));}
function build3D(a){DATA_scene=a.scene;
 if(!renderer){renderer=new THREE.WebGLRenderer({canvas:$('cv'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.setSize(1280,720,false);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputEncoding=THREE.sRGBEncoding;}
 scene=new THREE.Scene();scene.background=skyTexture();scene.fog=new THREE.Fog(0xbcd6ec,14,52);
 camera=new THREE.PerspectiveCamera(52,1280/720,0.1,120);
 scene.add(new THREE.HemisphereLight(0xbfd4f0,0x40502f,.75));
 const sun=new THREE.DirectionalLight(0xfff2e0,1.05);sun.position.set(6,10,4);sun.castShadow=true;
 sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-6;sun.shadow.camera.right=6;sun.shadow.camera.top=6;sun.shadow.camera.bottom=-6;
 sun.shadow.camera.near=1;sun.shadow.camera.far=40;sun.shadow.bias=-0.0004;scene.add(sun);scene.add(sun.target);
 // teren: relief poza arena, arena plaska (rider 4)
 const geo=new THREE.PlaneGeometry(60,60,140,140);const pos=geo.attributes.position;
 for(let i=0;i<pos.count;i++){pos.setZ(i,terrainH(pos.getX(i),pos.getY(i)));}geo.computeVertexNormals();
 const ground=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({map:groundTexture(),roughness:1}));
 ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
 // geofence ze stalych P2 (rider 2): arena 2.0 + shield-trigger geo_lim
 scene.add(squareRing(a.scene.arena_half,0x8b93a3,0.02));
 scene.add(squareRing(a.scene.geo_lim,0xeab308,0.03));
 // obiekty (kolor/ksztalt/pozycja bez zmian)
 a.scene.objects.forEach(o=>{const m=shapeMesh(o);m.position.copy(V(o.pos[0],o.pos[1],o.pos[2]));scene.add(m);});
 drone=makeDrone();scene.add(drone);
 const p0=a.trace[0].pos;camPos.copy(V(p0[0]-3.3,p0[1]-0.05,1.4));built=ai;update3D(0);}
function tiltFor(a,i){const T=a.trace;const c=T[i].pos,pv=T[Math.max(0,i-1)].pos,nx=T[Math.min(T.length-1,i+1)].pos;
 const ax=(nx[0]-2*c[0]+pv[0]),ay=(nx[1]-2*c[1]+pv[1]);const cl=v=>Math.max(-0.22,Math.min(0.22,v*9));return {pitch:cl(-ax),roll:cl(ay)};}
function update3D(i){const a=DATA.acts[ai];if(built!==ai)build3D(a);const p=a.trace[i].pos;
 drone.position.copy(V(p[0],p[1],p[2]));const t=tiltFor(a,i);drone.rotation.set(t.pitch,0,t.roll); // yaw=0
 const want=V(p[0]-3.3,p[1]-0.05,1.4);camPos.lerp(want,0.12);camera.position.copy(camPos);
 camAt.lerp(V(p[0]+1.6,p[1],0.72),0.2);camera.lookAt(camAt);renderer.render(scene,camera);}
// ---------- data layer (accepted) ----------
const MEAS=[
 {t:"designation envelope",m:"67% success / 10% wrong-lock · gate 85/8 frozen, unmet",s:"RAPORT_3B · 3C_MVP §2"},
 {t:"executability ceiling",m:"GT-fed 100% — task is feasible for the executor",s:"RAPORT_3B §9"},
 {t:"broken-stream curve (G2)",m:"80 / 66 / 44 / 30 (p0/.25/.5/.75); burst L5 −4 pp vs scattered p0.5 −36 pp · no shield",s:"RAPORT_S3B4"},
 {t:"shield accounting (dropout)",m:"16 of 28 base failures → abstention; success kept 15/22",s:"RAPORT_3C_MVP §5"},
 {t:"geofence traps",m:"25/25 correct REFUSE(GEOFENCE)",s:"RAPORT_3C_MVP §6"},
 {t:"absent-object limit (honest)",m:"6/25 — open-vocab grounder hallucinates a box; perception is not proved",s:"RAPORT_3C_MVP §6"}];
const PUNCH="local robustness of the network is not provable by sound IBP at this width — that is why a proved automaton (P1, P2, P5) stands between the network and actuation.";
function certCard(k,c){let v=(c.verdict||"").toUpperCase();let cls=v.indexOf("PROV")>=0?"vp":"vu";
 let extra=(k==="P3")?('<div class="punch">'+PUNCH+'</div>'):'';
 return '<div class="card"><span class="t">'+k+'</span> · <span class="'+cls+'">'+v+'</span><div class="m">'+(c.method||'')+'</div><div class="h">solver '+(c.solver||'')+' · hash '+(c.hash||'')+'</div>'+extra+'</div>';}
function fillBoard(){let pr='';["P1","P2","P5","P4","A4_memory","P3"].forEach(k=>{if(DATA.certs[k])pr+=certCard(k,DATA.certs[k]);});
 $('proved').innerHTML=pr;$('measured').innerHTML=MEAS.map(x=>'<div class="card"><span class="t">'+x.t+'</span><div class="m">'+x.m+'</div><div class="h">'+x.s+'</div></div>').join('');
 const dr=(DATA.dropped||[]);$('dropped').innerHTML=dr.length?('dropped scenes (bounded re-record, shield APPLIED, rules not softened): '+dr.map(d=>d.act+' expected '+EN(d.expect)+' → got '+EN(d.wynik)).join('; ')+'. reported, not hidden — the burst-bridging aggregate is the measured G2 curve above.'):'';}
function buildNav(){const n=$('nav');DATA.acts.forEach((a,i)=>{const b=document.createElement('button');b.textContent=a.title;
 b.onclick=()=>{showBoard(false);ai=i;fi=0;render();setActive();};n.appendChild(b);});
 const bb=document.createElement('button');bb.textContent='● proof board';bb.onclick=()=>showBoard(true);n.appendChild(bb);setActive();}
function setActive(){[...$('nav').children].forEach((b,i)=>b.classList.toggle('on',i===ai&&$('boardView').classList.contains('hidden')));}
function showBoard(on){$('boardView').classList.toggle('hidden',!on);$('stage').classList.toggle('hidden',on);pause();
 [...$('nav').children].forEach(b=>b.classList.remove('on'));if(on){$('nav').lastChild.classList.add('on');fillBoard();}else setActive();}
function render(){const a=DATA.acts[ai],fr=a.frames[fi]||a.frames[0],tr=a.trace[fi]||a.trace[a.trace.length-1];
 update3D(fi);
 $('banner').innerHTML=a.banner.replace(/(\d+%|\d+\/\d+|−?\d+ ?pp|0\.\d+→?0?\.?\d*|85\/8|2\.0 m)/g,'<b>$1</b>');
 $('src').textContent='source: '+a.source;$('note').textContent=a.note;
 $('v256').src=fr.c256;$('v64').src=fr.c64;
 // panele-instrumenty: obwódka/badge sterowane NAGRANYMI zdarzeniami z trace
 const lk2=tr.link||'seeking';const prev=a.trace[fi-1];
 const delivered=(fi>0&&tr.age_s!=null&&prev&&prev.age_s!=null&&tr.age_s<prev.age_s-0.05);
 let bcls,badge,btxt;
 if(tr.decision==='REFUSE'){bcls='b-stale';badge='refuse';btxt='REFUSE';}      // bursztyn
 else if(delivered){bcls='b-live';badge='live';btxt='● DELIVERED';}            // zielony tick
 else if(lk2==='frozen'){bcls='b-frozen';badge='frozen';btxt='LINK FROZEN';}   // czerwona obwódka
 else {bcls='b-'+lk2;badge=lk2;btxt=lk2.toUpperCase();}
 $('w256').className='imgwrap '+bcls;$('e256').className='evt '+badge;$('e256').textContent=btxt;
 $('r256a').innerHTML='LINK <b>'+lk2.toUpperCase()+'</b>';
 $('r256b').innerHTML='age '+(tr.age_s==null?'—':(+tr.age_s).toFixed(1)+'s')+' · conf '+(tr.conf==null?'—':(+tr.conf).toFixed(3));
 $('r64').textContent='frame '+fi;
 $('pCmd').textContent='"'+a.command+'"';$('pT').textContent=tr.t.toFixed(2)+' s / '+fi;
 const lk=tr.link||'seeking';$('pLink').textContent=lk.toUpperCase();$('pLink').className='pill link-'+lk;
 $('pAge').textContent=tr.age_s==null?'':'age '+(+tr.age_s).toFixed(1)+'s';
 $('pConf').textContent=tr.conf==null?'—':(+tr.conf).toFixed(3);
 $('pWL').textContent=tr.wrong_lock?'1  ⚠ other object':'0';$('pWL').style.color=tr.wrong_lock?'var(--red)':'var(--dim)';
 $('pState').textContent=tr.state;$('pRule').textContent=tr.rule||'—';
 $('pDec').textContent=tr.decision;$('pDec').className='v dec-'+tr.decision;$('pReason').textContent=EN(tr.reason)||'—';
 $('pTip').classList.toggle('hidden',!(tr.decision==='HOLD'&&tr.state==='DWELL-GUARD'));
 const c=a.admission.map(r=>'<div class="cl">▸ '+(r.phase)+': "'+(r.cmd||'')+'" → <span class="d-'+r.decision+'">'+r.decision+(r.reason?'('+r.reason+')':'')+'</span> <span style="color:var(--dim)">sig '+r.sig+'</span></div>').join('');
 $('console').innerHTML='<div style="color:var(--dim);margin-bottom:3px">CONSOLE · signed admission chain</div>'+(c||'—');
 const p=a.prov;$('prov').textContent='PROVENANCE  pool '+p.pool+' · seed '+p.seed+' · '+(p.K!=null?p.K+'/'+p.A+' · ':'')+'mask '+p.mask+' · outcome '+EN(p.outcome)+' · attempt '+p.attempts+'/3 · authz '+(p.authz?'ok':'FAIL')+' · scene '+p.sceneSha;
 $('scrub').max=a.frames.length-1;$('scrub').value=fi;}
function tick(){const a=DATA.acts[ai];fi++;if(fi>=a.frames.length){fi=a.frames.length-1;pause();render();return;}render();}
function play(){if(playing)return;playing=true;$('play').textContent='❚❚ pause';$('play').classList.add('on');timer=setInterval(tick,Math.round(1000/12/spd));}
function pause(){playing=false;if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ play';$('play').classList.remove('on');}
$('play').onclick=()=>{if(playing)pause();else{if(fi>=DATA.acts[ai].frames.length-1)fi=0;play();}};
$('step').onclick=()=>{pause();fi=Math.min(fi+1,DATA.acts[ai].frames.length-1);render();};
$('scrub').oninput=e=>{pause();fi=+e.target.value;render();};
$('spd').onclick=()=>{spd=spd===1?2:spd===2?0.5:1;$('spd').textContent=spd+'×';if(playing){pause();play();}};
document.onkeydown=e=>{if(e.key===' '){e.preventDefault();$('play').click();}if(e.key==='ArrowRight')$('step').click();};
(function(){var h=decodeURIComponent(location.hash.slice(1));if(h){var pp=h.split('/');var idx=DATA.acts.findIndex(a=>a.id===pp[0]);if(idx>=0)ai=idx;if(pp[1]!=null&&pp[1]!=='')fi=+pp[1];}})();
buildNav();render();
</script></body></html>"""


if __name__ == "__main__":
    build()
