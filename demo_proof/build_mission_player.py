"""demo_proof/build_mission_player.py — player MISJI (tryb mission, self-contained).

Jedna ciągła rejestracja: widok 3D Three.js z trace.pos (dron), scena z scene.json, geofence ze
stałych P2; panele 256²/64² (nagrane klatki, reduced fps, mapa frame_at); napisy z subtitles.vtt
(generowane z logu zdarzeń); badge segmentu (LEARNED-LEG / SCRIPTED-TRANSIT / ADMISSION-REFUSE) +
etykieta „reposition to launch (executor) — not the learned pilot". Instrumenty W2. Link do
trybu aktów DP (liquidsight_proof.html) — akty nietknięte. Zero pomiaru.

CLI: .venv/bin/python -m demo_proof.build_mission_player
"""
from __future__ import annotations
import base64
import glob
import hashlib
import json
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
M = os.path.join(_ROOT, "results", "demo_proof", "mission")
THREE_JS = os.path.join(os.path.dirname(__file__), "vendor", "three.min.js")
OUT_HTML = os.path.join(_ROOT, "demo_proof", "liquidsight_mission.html")


def b64(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def build():
    mj = json.load(open(os.path.join(M, "mission.json")))
    scene = json.load(open(os.path.join(M, "scene.json")))
    subs = open(os.path.join(M, "subtitles.vtt")).read() if os.path.exists(os.path.join(M, "subtitles.vtt")) else ""
    n256 = len(glob.glob(os.path.join(M, "cam256", "f*.jpg")))
    frames = [{"c256": b64(os.path.join(M, "cam256", f"f{i:04d}.jpg")),
               "c64": b64(os.path.join(M, "cam64", f"f{i:04d}.jpg"))} for i in range(n256)]
    # per-tick -> frame index (frame_at ma g co SAVE_EVERY); wypełnij do najbliższego wcześniejszego
    fa = {int(k): v for k, v in mj["frame_at"].items()}
    ntk = mj["n_ticks"]; per_tick = [0] * ntk; last = 0
    for g in range(ntk):
        if g in fa:
            last = fa[g]
        per_tick[g] = last
    data = {"trace": mj["trace"], "events": mj["events"], "perTick": per_tick, "frames": frames,
            "scene": scene, "results": mj["results"], "admissions": mj["admissions"],
            "authz": mj["authz_ok"], "seed": mj["seed"], "sceneSha": mj["scene_sha256"][:12],
            "burst": mj["burst_L2"]}
    three = open(THREE_JS).read()
    html = (HTML.replace("/*THREE*/", three)
                .replace("/*DATA*/", "const D=" + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + ";"))
    open(OUT_HTML, "w").write(html)
    sha = hashlib.sha256(open(OUT_HTML, "rb").read()).hexdigest()
    print(f"ZAPIS -> {OUT_HTML}  ({os.path.getsize(OUT_HTML)/1e6:.1f} MB)  sha256={sha}")
    print(f"ticks={ntk} frames={n256} events={len(mj['events'])}")


HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>LiquidSight — mission cut</title>
<style>
:root{--bg:#0b0e14;--panel:#12161f;--edge:#232a36;--txt:#e6e9ef;--dim:#8b93a3;--green:#22c55e;--red:#ef4444;--yellow:#eab308;--blue:#3b82f6;--mono:ui-monospace,Menlo,Consolas,monospace}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font-family:system-ui,Segoe UI,Roboto,sans-serif;font-size:14px}
.wrap{max-width:1180px;margin:0 auto;padding:14px}h1{font-size:16px;margin:0 0 2px}.sub{color:var(--dim);font-size:12px;margin-bottom:10px}
.top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:10px}.left{display:flex;flex-direction:column;gap:10px}
.view3d{border:1px solid var(--edge);border-radius:6px;overflow:hidden;position:relative;background:#0a0d13;aspect-ratio:16/9}
.view3d canvas{width:100%!important;height:100%!important;display:block}
.tag{position:absolute;top:6px;left:8px;font-family:var(--mono);font-size:11px;color:#cfe;background:rgba(0,0,0,.5);padding:2px 6px;border-radius:4px}
.seg{position:absolute;top:6px;right:8px;font-family:var(--mono);font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600}
.seg.learned{background:rgba(34,197,94,.2);color:var(--green)}.seg.transit{background:rgba(59,130,246,.2);color:var(--blue)}.seg.refuse{background:rgba(239,68,68,.25);color:var(--red)}
.subbar{position:absolute;left:0;right:0;bottom:0;padding:8px 12px;background:linear-gradient(transparent,rgba(0,0,0,.75));text-align:center}
.subtxt{font-family:var(--mono);font-size:13px;color:#fff;text-shadow:0 1px 3px #000}
.terr{position:absolute;bottom:34px;right:8px;font-family:var(--mono);font-size:10px;color:#cde;background:rgba(0,0,0,.5);padding:2px 6px;border-radius:4px}
.panel{background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:12px;font-family:var(--mono)}
.row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--edge);font-size:12.5px}.row:last-child{border-bottom:none}.k{color:var(--dim)}.v{color:#fff;text-align:right}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.link-live{background:rgba(34,197,94,.15);color:var(--green)}.link-stale{background:rgba(234,179,8,.15);color:var(--yellow)}.link-frozen{background:rgba(239,68,68,.15);color:var(--red)}.link-seeking,.link-na{background:rgba(139,147,163,.15);color:var(--dim)}
.dec-ALLOW{color:var(--green)}.dec-HOLD{color:var(--yellow)}.dec-REFUSE{color:var(--red)}.dec-TRANSIT,.dec-LAND{color:var(--blue)}
.instr{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.inst{position:relative;background:#0a0d13;border:1px solid var(--edge);border-radius:6px;padding:7px}
.inst .lbl{font-family:var(--mono);font-size:9px;color:var(--dim);margin-bottom:5px;text-transform:uppercase;line-height:1.25}
.imgwrap{position:relative;border:2px solid var(--edge);border-radius:3px;overflow:hidden;line-height:0}.imgwrap img{width:100%;display:block}.inst.pix .imgwrap img{image-rendering:pixelated}
.grid64{position:absolute;inset:0;pointer-events:none;background-image:repeating-linear-gradient(0deg,rgba(180,200,230,.10) 0 1px,transparent 1px calc(100%/64)),repeating-linear-gradient(90deg,rgba(180,200,230,.10) 0 1px,transparent 1px calc(100%/64))}
.corner{position:absolute;width:9px;height:9px;border:1.5px solid rgba(207,224,255,.55);z-index:2}.corner.tl{top:2px;left:2px;border-right:none;border-bottom:none}.corner.tr{top:2px;right:2px;border-left:none;border-bottom:none}.corner.bl{bottom:2px;left:2px;border-right:none;border-top:none}.corner.br{bottom:2px;right:2px;border-left:none;border-top:none}
.b-live{border-color:var(--green)!important}.b-stale{border-color:var(--yellow)!important}.b-frozen{border-color:var(--red)!important}
.controls{display:flex;gap:8px;align-items:center;margin-top:10px;flex-wrap:wrap}button{background:#1b2130;color:var(--txt);border:1px solid var(--edge);border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}button:hover{background:#242c3d}button.on{border-color:var(--blue);color:#fff}
.scrub{flex:1;min-width:160px}input[type=range]{width:100%}a{color:var(--blue)}
.prov{margin-top:10px;font-family:var(--mono);font-size:11px;color:var(--dim);background:var(--panel);border:1px solid var(--edge);border-radius:6px;padding:8px 10px}
</style></head><body><div class="wrap">
<div class="top"><div><h1>LiquidSight — mission cut · one continuous recording</h1>
<div class="sub">learned pilot within its measured envelope · scripted transits between · shield APPLIED · subtitles generated from the event log</div></div>
<div class="sub">alt view: <a href="liquidsight_proof.html">DP acts (proof board)</a></div></div>
<div class="grid">
 <div class="left">
  <div class="view3d"><span class="tag">external 3D · re-rendered from recorded states</span><span class="seg" id="seg"></span><canvas id="cv"></canvas>
   <span class="terr">terrain = third-person visualization; the network sees the 64² camera</span>
   <div class="subbar"><span class="subtxt" id="subtxt"></span></div></div>
  <div class="controls"><button id="play">▶ play</button><button id="step">⟶ step</button>
   <span class="scrub"><input type="range" id="scrub" min="0" value="0"></span><button id="spd">1×</button></div>
 </div>
 <div>
  <div class="panel">
   <div class="row"><span class="k">t / tick</span><span class="v" id="pT"></span></div>
   <div class="row"><span class="k">segment</span><span class="v" id="pSeg"></span></div>
   <div class="row"><span class="k">LINK</span><span class="v"><span id="pLink" class="pill"></span> <span id="pAge"></span></span></div>
   <div class="row"><span class="k">conf</span><span class="v" id="pConf"></span></div>
   <div class="row"><span class="k">SHIELD state</span><span class="v" id="pState"></span></div>
   <div class="row"><span class="k">decision</span><span class="v" id="pDec"></span></div>
   <div class="row"><span class="k">reason</span><span class="v" id="pReason"></span></div>
  </div>
  <div class="instr">
   <div class="inst"><div class="lbl">RAW FEED · semantic cam 256²</div>
    <div class="imgwrap" id="w256"><img id="v256"><span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div></div>
   <div class="inst pix"><div class="lbl">RAW FEED · policy input 64×64 — what the network sees</div>
    <div class="imgwrap"><img id="v64"><div class="grid64"></div><span class="corner tl"></span><span class="corner tr"></span><span class="corner bl"></span><span class="corner br"></span></div></div>
  </div>
  <div class="prov" id="prov"></div>
 </div>
</div></div>
<script>/*THREE*/</script>
<script>
/*DATA*/
let g=0,playing=false,spd=1,timer=null;const $=id=>document.getElementById(id);
const V=(sx,sy,sz)=>new THREE.Vector3(sx,sz,sy);
let renderer,scene,camera,drone,camPos=new THREE.Vector3(),camAt=new THREE.Vector3();
function groundTexture(){const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d');x.fillStyle='#3d5a34';x.fillRect(0,0,256,256);for(let i=0;i<9000;i++){const px=Math.random()*256,py=Math.random()*256,r=Math.random()*2.2,v=Math.random();x.fillStyle=v<.5?'rgba(60,92,50,.7)':v<.8?'rgba(78,110,60,.6)':'rgba(120,105,70,.5)';x.beginPath();x.arc(px,py,r,0,7);x.fill();}const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(10,10);return t;}
function skyTexture(){const c=document.createElement('canvas');c.width=16;c.height=256;const x=c.getContext('2d');const g2=x.createLinearGradient(0,0,0,256);g2.addColorStop(0,'#2a5a9e');g2.addColorStop(.55,'#6f9fd0');g2.addColorStop(.72,'#bcd6ec');g2.addColorStop(1,'#d9e6d0');x.fillStyle=g2;x.fillRect(0,0,16,256);return new THREE.CanvasTexture(c);}
function terrainH(px,py){const d=Math.max(Math.abs(px),Math.abs(py));if(d<=2.4)return 0;const t=d-2.4;return ((Math.sin(px*0.6)*Math.cos(py*0.55)+1)*0.5)*Math.min(t*0.55,3.2)+t*0.16;}
function makeDrone(){const gp=new THREE.Group();const body=new THREE.Mesh(new THREE.BoxGeometry(.16,.05,.16),new THREE.MeshStandardMaterial({color:0x1b1f2a,metalness:.4,roughness:.5}));body.castShadow=true;gp.add(body);const arm=new THREE.MeshStandardMaterial({color:0x2b3340}),rot=new THREE.MeshStandardMaterial({color:0x0e1118});[[.13,.13],[.13,-.13],[-.13,.13],[-.13,-.13]].forEach(([a,b])=>{const r=new THREE.Mesh(new THREE.CylinderGeometry(.07,.07,.012,20),rot);r.position.set(a,.03,b);r.castShadow=true;gp.add(r);});const led=new THREE.Mesh(new THREE.SphereGeometry(.022,10,10),new THREE.MeshStandardMaterial({color:0x22c55e,emissive:0x22c55e,emissiveIntensity:.9}));led.position.set(.1,0,0);gp.add(led);gp.scale.setScalar(1.5);return gp;}
function shapeMesh(o){const c=D.scene.render.shapes;let ge;if(o.shape==='sphere')ge=new THREE.SphereGeometry(c.sphere.radius,24,18);else if(o.shape==='cylinder')ge=new THREE.CylinderGeometry(c.cylinder.radius,c.cylinder.radius,c.cylinder.length,24);else ge=new THREE.BoxGeometry(c.box.half[0]*2,c.box.half[2]*2,c.box.half[1]*2);const rgb=D.scene.render.colors[o.color];const m=new THREE.MeshStandardMaterial({color:new THREE.Color(rgb[0],rgb[1],rgb[2]),roughness:.55});const me=new THREE.Mesh(ge,m);me.castShadow=me.receiveShadow=true;return me;}
function ring(lim,col,y){const pts=[[lim,lim],[lim,-lim],[-lim,-lim],[-lim,lim],[lim,lim]].map(([a,b])=>V(a,b,y));return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(pts),new THREE.LineBasicMaterial({color:col}));}
function build3D(){renderer=new THREE.WebGLRenderer({canvas:$('cv'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(1280,720,false);renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.outputEncoding=THREE.sRGBEncoding;
 scene=new THREE.Scene();scene.background=skyTexture();scene.fog=new THREE.Fog(0xbcd6ec,14,52);camera=new THREE.PerspectiveCamera(52,1280/720,.1,120);
 scene.add(new THREE.HemisphereLight(0xbfd4f0,0x40502f,.75));const sun=new THREE.DirectionalLight(0xfff2e0,1.05);sun.position.set(6,10,4);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-6;sun.shadow.camera.right=6;sun.shadow.camera.top=6;sun.shadow.camera.bottom=-6;sun.shadow.camera.far=40;sun.shadow.bias=-.0004;scene.add(sun,sun.target);
 const geo=new THREE.PlaneGeometry(60,60,140,140),ps=geo.attributes.position;for(let i=0;i<ps.count;i++)ps.setZ(i,terrainH(ps.getX(i),ps.getY(i)));geo.computeVertexNormals();const gr=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({map:groundTexture(),roughness:1}));gr.rotation.x=-Math.PI/2;gr.receiveShadow=true;scene.add(gr);
 scene.add(ring(D.scene.arena_half,0x8b93a3,.02));scene.add(ring(D.scene.geo_lim,0xeab308,.03));
 D.scene.objects.forEach(o=>{const m=shapeMesh(o);m.position.copy(V(o.pos[0],o.pos[1],o.pos[2]));scene.add(m);});
 drone=makeDrone();scene.add(drone);const p0=D.trace[0].pos;camPos.copy(V(p0[0]-3.3,p0[1]-.05,1.4));update3D(0);}
function tiltFor(i){const T=D.trace,c=T[i].pos,pv=T[Math.max(0,i-1)].pos,nx=T[Math.min(T.length-1,i+1)].pos,ax=nx[0]-2*c[0]+pv[0],ay=nx[1]-2*c[1]+pv[1],cl=v=>Math.max(-.22,Math.min(.22,v*9));return{pitch:cl(-ax),roll:cl(ay)};}
function update3D(i){const p=D.trace[i].pos;drone.position.copy(V(p[0],p[1],p[2]));const t=tiltFor(i);drone.rotation.set(t.pitch,0,t.roll);
 const want=V(p[0]-3.3,p[1]-.05,1.4);camPos.lerp(want,.12);camera.position.copy(camPos);camAt.lerp(V(p[0]+1.6,p[1],.72),.2);camera.lookAt(camAt);renderer.render(scene,camera);}
function curSub(t){let s='';for(const e of D.events){if(e.t<=t)s=e.text;else break;}return s;}
const SEGCLS={"LEARNED-LEG":"learned","SCRIPTED-TRANSIT":"transit","ADMISSION-REFUSE":"refuse"};
function render(){const tr=D.trace[g];update3D(g);const fi=D.perTick[g],fr=D.frames[fi]||D.frames[0];
 $('v256').src=fr.c256;$('v64').src=fr.c64;
 const seg=tr.seg;$('seg').textContent=seg;$('seg').className='seg '+(SEGCLS[seg]||'transit');
 $('subtxt').textContent=curSub(tr.g/12);
 $('pT').textContent=(tr.g/12).toFixed(2)+' s / '+tr.g;$('pSeg').textContent=seg;
 const lk=tr.link||'seeking';$('pLink').textContent=lk.toUpperCase();$('pLink').className='pill link-'+(lk==='n/a'?'na':lk);
 $('pAge').textContent=tr.age_s==null?'':'age '+(+tr.age_s).toFixed(1)+'s';
 $('pConf').textContent=tr.conf==null?'—':(+tr.conf).toFixed(3);
 $('pState').textContent=tr.state||'—';$('pDec').textContent=tr.decision;$('pDec').className='v dec-'+tr.decision;$('pReason').textContent=tr.reason||'—';
 $('w256').className='imgwrap '+(lk==='frozen'?'b-frozen':lk==='live'?'b-live':lk==='stale'?'b-stale':'');
 $('prov').textContent='MISSION  seed '+D.seed+' · scene '+D.sceneSha+' · authz '+(D.authz?'ok':'FAIL')+' · burst L2 seed '+D.burst.mask_seed+' off '+D.burst.offset+' · segments: learned-leg = gc5 pilot, scripted-transit = executor';
 $('scrub').max=D.trace.length-1;$('scrub').value=g;}
function tick(){g++;if(g>=D.trace.length){g=D.trace.length-1;pause();render();return;}render();}
function play(){if(playing)return;playing=true;$('play').textContent='❚❚ pause';$('play').classList.add('on');timer=setInterval(tick,Math.round(1000/12/spd));}
function pause(){playing=false;if(timer)clearInterval(timer);timer=null;$('play').textContent='▶ play';$('play').classList.remove('on');}
$('play').onclick=()=>{if(playing)pause();else{if(g>=D.trace.length-1)g=0;play();}};
$('step').onclick=()=>{pause();g=Math.min(g+1,D.trace.length-1);render();};
$('scrub').oninput=e=>{pause();g=+e.target.value;render();};
$('spd').onclick=()=>{spd=spd===1?2:spd===2?0.5:1;$('spd').textContent=spd+'×';if(playing){pause();play();}};
document.onkeydown=e=>{if(e.key===' '){e.preventDefault();$('play').click();}if(e.key==='ArrowRight')$('step').click();};
(function(){var h=+location.hash.slice(1);if(h>0)g=Math.min(h,D.trace.length-1);})();build3D();render();
</script></body></html>"""


if __name__ == "__main__":
    build()
