/* broll kit：所有风格共用的零件。
   每个画面都是时间 t 的纯函数：seek(t) 画出第 t 秒的样子，不用定时器、不用 CSS 过渡，
   所以能一帧一帧精确截图。弹簧/淡入函数来自 motion.js（Bart Slodyczka, MIT）。 */
(function(){
const K = window.K = {};
const M = window.M;
K.clamp = (x,a=0,b=1)=>Math.min(b,Math.max(a,x));
K.eo = x=>{x=K.clamp(x);return 1-Math.pow(1-x,3)};
K.eio = x=>{x=K.clamp(x);return x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2};

// ---------- 读一句话 ----------
const UNIT = '%|％|倍|万亿|亿|万|千|百|元|块|美元|刀|年|个月|月|天|小时|分钟|秒|岁|个|次|人|倍速|k|K|w|W';
K.numbers = s=>{
  const re = new RegExp(`(\\d+(?:[.,]\\d+)?)\\s*(${UNIT})?`,'g'); const out=[]; let m;
  while((m=re.exec(s))){const v=parseFloat(m[1].replace(',','')); out.push({value:v, unit:m[2]||'', raw:m[0], index:m.index,
    digits:(m[1].split(/[.,]/)[1]||'').length});}
  return out;
};
// 数字前面几个字当它的名字，比如「年化 8%」→「年化」
K.labelBefore = (s,n,max=6)=>{
  const pre = s.slice(0,n.index).replace(/\s+$/,'').split(/[，,。；;：:！!？?、\s]/).pop() || '';
  return pre.replace(/(年化|长期|大约|约|大概|差不多|只有|高达|达到|是|有)+$/,'').replace(/^(存|买|卖|投|是|有|就|才|要|能|从|到|只|约|大约|差不多|达到|变成|涨到|跌到)+/,'').slice(-max) || '';
};
const CONNECT = /(就是|所以|然后|但是|因为|于是|接着|最后|再|→|->|=>)/;
K.chunks = (s,max=4)=>{
  let parts = s.split(/[，,。；;：:！!？?、\n]/).map(x=>x.trim()).filter(Boolean);
  if(parts.length<2) parts = s.split(CONNECT).map(x=>x.trim()).filter(x=>x&&!CONNECT.test(x));
  // 太碎的并到前一段
  const out=[]; for(const p of parts){ if(out.length && (p.length<=2 || out[out.length-1].length<=2)) out[out.length-1]+=p; else out.push(p); }
  while(out.length>max){ // 合并最短的相邻两段
    let bi=0,bl=1e9; for(let i=0;i<out.length-1;i++){const l=out[i].length+out[i+1].length; if(l<bl){bl=l;bi=i;}}
    out.splice(bi,2,out[bi]+'，'+out[bi+1]);
  }
  return out.length?out:[s];
};
// 纯动画模式：每段只留核心词
K.short = (s,max=8)=>{
  let t = s.replace(/^(其实|就是|所以|然后|但是|因为|那|这个|我们|你|我|它|他们)+/,'').replace(/(了|的|啊|呢|吧|嘛)$/,'');
  return t.length>max ? t.slice(0,max) : t;
};

// ---------- 风格 → 画面变量 ----------
const SANS = '"Source Han Sans SC","Noto Sans CJK SC","思源黑体","PingFang SC","Microsoft YaHei",sans-serif';
const SERIF = '"Source Han Serif SC","Noto Serif CJK SC","思源宋体","Songti SC",serif';
const MONO = '"JetBrains Mono","SF Mono",Menlo,Consolas,"Source Han Sans SC","Noto Sans CJK SC",monospace';
const fam = f => f==='serif'?SERIF : f==='mono'?MONO : (!f||f==='sans')?SANS : f;
K.applyStyle = (st, scene)=>{
  const r = document.documentElement.style, p = st.palette, set=(k,v)=>r.setProperty(k,v);
  set('--bg', p.bg); set('--ink', p.ink); set('--accent', p.accent);
  set('--accent2', p.accent2||p.accent); set('--muted', p.muted||p.ink); set('--panel', p.panel||p.bg);
  set('--line-c', p.line||p.muted||p.ink); set('--marker', p.marker||p.accent);
  const f = st.type||{};
  set('--font', fam(f.body||f.family)); set('--font-head', fam(f.head||f.family)); set('--mono', fam('mono'));
  if(f.mono) set('--mono', f.mono);
  set('--wh', f.head_weight||700); set('--wb', f.body_weight||400);
  set('--tracking', (f.tracking!=null?f.tracking:0)+'em'); set('--tracking-head', (f.head_tracking!=null?f.head_tracking:-0.01)+'em');
  const u = Math.min(scene.w, scene.h)/1080; K.u = u; set('--u', u+'px');
  set('--line', ((st.line&&st.line.width)||3)*u+'px');
  // 面板（卡片）的质感：glass 毛玻璃 / paper 纸片 / flat 纯色 / outline 线框 / none
  const sf = st.surface||{kind:'outline'}; K.surface = sf.kind||'outline';
  set('--radius', ((sf.radius!=null?sf.radius:22)*u)+'px');
  const sh = sf.shadow!=null?sf.shadow:0.25;
  set('--shadow', sh>0 ? `0 ${18*u}px ${60*u}px rgba(0,0,0,${(0.55*sh).toFixed(3)}), 0 ${2*u}px ${6*u}px rgba(0,0,0,${(0.25*sh).toFixed(3)})` : 'none');
  set('--surf-bg', sf.fill || (K.surface==='glass'?'rgba(255,255,255,.06)':K.surface==='paper'?'#FFFFFF':K.surface==='flat'?(p.panel||p.bg):'transparent'));
  set('--surf-border', sf.border || (K.surface==='glass'?'rgba(255,255,255,.14)':K.surface==='outline'?'var(--ink)':'transparent'));
  set('--surf-blur', K.surface==='glass' ? `blur(${24*u}px) saturate(140%)` : 'none');
  K.hlStyle = st.accent_style || 'fill';     // marker 荧光笔 / underline 下划线 / glow 发光 / fill 变色
  const L = st.layout_rules||{}; K.margin = (L.margin||0.09)*Math.min(scene.w,scene.h); K.align = L.align||'center';
  K.speed = (st.motion&&st.motion.speed)||1; K.entrance = (st.motion&&st.motion.entrance)||'rise';
  K.cuts = (st.motion&&st.motion.cuts_per_5s)||2; K.textScale = f.scale||1;
  K.background(st.background||{}, scene);
};
K.background = (bg, scene)=>{
  const s = document.getElementById('stage'), u=K.u, W=scene.w, H=scene.h;
  let css = 'var(--bg)';
  if(bg.glow && bg.glow.length){   // 柔光：两三团大光斑，像打了灯
    const spots = bg.glow.map((c,i)=>{ const pos=[['18%','12%'],['88%','78%'],['70%','8%']][i%3]; return `radial-gradient(ellipse ${Math.round(W*0.9)}px ${Math.round(H*0.6)}px at ${pos[0]} ${pos[1]}, ${c}, transparent 70%)`; });
    css = spots.join(',') + ',' + (bg.base||'var(--bg)');
  } else if(bg.gradient){ css = `linear-gradient(${bg.gradient.angle||180}deg, ${bg.gradient.from}, ${bg.gradient.to})`; }
  s.style.background = css;
  const tex = bg.texture||'plain', c = bg.texture_color||'rgba(127,127,127,.12)';
  const layer = document.createElement('div'); layer.className='tex';
  if(tex==='grid') layer.style.backgroundImage=`linear-gradient(${c} 1px,transparent 1px),linear-gradient(90deg,${c} 1px,transparent 1px)`, layer.style.backgroundSize=`${60*u}px ${60*u}px`;
  if(tex==='dots') layer.style.backgroundImage=`radial-gradient(${c} ${2*u}px,transparent ${2.4*u}px)`, layer.style.backgroundSize=`${40*u}px ${40*u}px`;
  if(tex==='scanlines') layer.style.backgroundImage=`repeating-linear-gradient(0deg,${c} 0 1px,transparent 1px ${4*u}px)`;
  s.appendChild(layer);
  const g = bg.grain!=null ? bg.grain : (tex==='paper'?0.10:tex==='grain'?0.14:0);
  if(g>0){ const n=document.createElement('div'); n.className='tex'; n.style.mixBlendMode=bg.grain_blend||'multiply';
    n.innerHTML=`<svg width="100%" height="100%"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="${bg.grain_scale||0.85}" numOctaves="2" seed="7" stitchTiles="stitch"/><feColorMatrix values="0 0 0 0 0.5 0 0 0 0 0.5 0 0 0 0 0.5 0 0 0 ${g} 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`;
    s.appendChild(n); K._grain=n; }
  if(bg.vignette){ const v=document.createElement('div'); v.className='tex'; v.style.background=`radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,${bg.vignette}) 100%)`; s.appendChild(v); }
};
// 统一的卡片外观
K.surf = (el)=>{ el.classList.add('surf'); return el; };
// 强调一段字：按风格用荧光笔 / 下划线 / 发光 / 变色；p 是 0..1 的进度
K.mark = (txt, hit)=>{ if(!hit || txt.indexOf(hit)<0) return K.esc(txt); const i=txt.indexOf(hit);
  return K.esc(txt.slice(0,i))+`<span class="hl hl-${K.hlStyle}"><span class="hlbg"></span><span class="hltx">${K.esc(hit)}</span></span>`+K.esc(txt.slice(i+hit.length)); };
K.markSeek = (root, p)=>{ root.querySelectorAll('.hl').forEach(h=>{ const bg=h.querySelector('.hlbg'); if(bg) bg.style.transform=`scaleX(${K.eio(p).toFixed(4)})`;
  if(K.hlStyle==='glow'||K.hlStyle==='fill'){ h.querySelector('.hltx').style.color = p>0.02?'var(--accent)':''; h.style.textShadow = K.hlStyle==='glow'&&p>0.02?`0 0 ${(18*K.u*p).toFixed(1)}px var(--accent)`:''; } }); };
K.CSS = `
  .surf{background:var(--surf-bg);border:max(1px,calc(var(--u)*1.5)) solid var(--surf-border);border-radius:var(--radius);box-shadow:var(--shadow);-webkit-backdrop-filter:var(--surf-blur);backdrop-filter:var(--surf-blur);box-sizing:border-box}
  .hl{position:relative;display:inline-block;white-space:nowrap}
  .hl .hlbg{position:absolute;left:-0.08em;right:-0.08em;transform-origin:0 50%;transform:scaleX(0);z-index:0}
  .hl .hltx{position:relative;z-index:1}
  .hl-marker .hlbg{top:0.16em;bottom:0.02em;background:var(--marker);opacity:.92;border-radius:0.06em}
  .hl-marker .hltx{color:var(--ink)}
  .hl-underline .hlbg{bottom:-0.06em;height:0.12em;background:var(--accent);border-radius:99px}
  .hl-fill .hlbg,.hl-glow .hlbg{display:none}
  .head{font-family:var(--font-head);font-weight:var(--wh);letter-spacing:var(--tracking-head);color:var(--ink)}
  .body{font-family:var(--font);font-weight:var(--wb);letter-spacing:var(--tracking);color:var(--ink)}
  .kick{font-family:var(--mono);color:var(--accent);letter-spacing:.12em;text-transform:uppercase}
  .mut{color:var(--muted)}
`;

// ---------- 时间 ----------
// 把 n 个节拍排进时长：开头留一点，结尾留一点定格
K.beats = (n, dur)=>{
  const sp = K.speed, head = Math.min(0.25, dur*0.08)/sp, tail = Math.max(0.5, dur*0.22);
  const span = Math.max(0.3, dur - head - tail); const step = n>1 ? span/(n-1) : 0;
  return Array.from({length:n},(_,i)=>head + i*step);
};
// 进场：返回 {o, tx, ty, s, blur, draw(0..1)}
K.enter = (t, t0, kind=K.entrance)=>{
  const d = 0.45/K.speed, x = (t-t0)/d;
  if(kind==='blur' && M){ const v=M.vis(t,t0,null); return {o:v.o,tx:0,ty:0,s:v.s,blur:v.blur,draw:K.eo(x)}; }
  if(kind==='pop' && M){ const k=M.S(t-t0,22*K.speed,0.55); return {o:K.clamp(x*3),tx:0,ty:0,s:0.6+0.4*k,blur:0,draw:K.eo(x)}; }
  if(kind==='draw') return {o:K.clamp(x*2.5),tx:0,ty:0,s:1,blur:0,draw:K.eio(x*0.8)};
  if(kind==='type') return {o:K.clamp(x*4),tx:0,ty:0,s:1,blur:0,draw:K.clamp(x*0.7)};
  const e=K.eo(x); return {o:K.clamp(x*2), tx:0, ty:(1-e)*40*K.u, s:1, blur:0, draw:e}; // rise
};
K.put = (el, v)=>{ el.style.opacity=v.o.toFixed(3); el.style.transform=`translate(${v.tx.toFixed(1)}px,${v.ty.toFixed(1)}px) scale(${v.s.toFixed(3)})`;
  el.style.filter = v.blur>0.05?`blur(${v.blur.toFixed(1)}px)`:'none'; };
// SVG 描线：path 先 setup 一次，之后给 0..1
K.strokeSetup = el=>{ const L=el.getTotalLength?el.getTotalLength():1000; el.style.strokeDasharray=L; el.style.strokeDashoffset=L; el._L=L; };
K.stroke = (el,p)=>{ el.style.strokeDashoffset = (el._L*(1-K.clamp(p))).toFixed(2); };
// 数字滚动
K.countText = (n, p)=>{ const v = n.value*K.eo(p); return (n.digits? v.toFixed(n.digits) : Math.round(v).toString()) + n.unit; };

// 文字放得下：按字数估字号
K.fit = (text, boxW, maxPx, minPx=28)=>{ const n=Math.max(1,[...text].length); return Math.max(minPx*K.u, Math.min(maxPx*K.u*K.textScale, boxW/(n*1.02))); };

K.el = (tag, cls, html, parent)=>{ const e=document.createElement(tag); if(cls) e.className=cls; if(html!=null) e.innerHTML=html; (parent||document.getElementById('stage')).appendChild(e); return e; };
K.svg = (parent, w, h)=>{ const s=document.createElementNS('http://www.w3.org/2000/svg','svg'); s.setAttribute('width',w); s.setAttribute('height',h);
  s.setAttribute('viewBox',`0 0 ${w} ${h}`); s.style.position='absolute'; s.style.left='0'; s.style.top='0'; s.style.overflow='visible'; parent.appendChild(s); return s; };
K.path = (svg, d, cls)=>{ const p=document.createElementNS('http://www.w3.org/2000/svg','path'); p.setAttribute('d',d); if(cls) p.setAttribute('class',cls); svg.appendChild(p); return p; };
K.esc = s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

// 统一入口：模板注册 LAYOUT，渲染器调用 seek(t)
window.seek = t=>{ if(window.LAYOUT) window.LAYOUT.seek(t); };
K.start = ()=>{
  const sc = window.SCENE, st = window.STYLE;
  const stage = document.getElementById('stage'); stage.style.width=sc.w+'px'; stage.style.height=sc.h+'px';
  K.applyStyle(st, sc);
  const ks=document.createElement('style'); ks.textContent=K.CSS; document.head.appendChild(ks);
  window.LAYOUT.build(stage, sc, st);
  window.KEYTIMES = window.LAYOUT.keyTimes ? window.LAYOUT.keyTimes(sc.dur) : [sc.dur*0.3, sc.dur*0.62, sc.dur-0.04];
  seek(0);
};
})();
