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
  return pre.replace(/^(是|有|就|才|要|能|从|到|只|约|大约|差不多|达到|变成|涨到|跌到)+/,'').slice(-max) || '';
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
K.applyStyle = (st, scene)=>{
  const r = document.documentElement.style, p = st.palette;
  r.setProperty('--bg', p.bg); r.setProperty('--ink', p.ink); r.setProperty('--accent', p.accent);
  r.setProperty('--accent2', p.accent2||p.accent); r.setProperty('--muted', p.muted||p.ink);
  r.setProperty('--panel', p.panel||p.bg);
  const f = st.type||{};
  r.setProperty('--font', f.family || '"Source Han Sans SC","Noto Sans CJK SC","思源黑体","PingFang SC","Microsoft YaHei",sans-serif');
  r.setProperty('--mono', f.mono || '"JetBrains Mono","SF Mono",Menlo,Consolas,"Source Han Sans SC","Noto Sans CJK SC",monospace');
  r.setProperty('--wh', f.head_weight||700); r.setProperty('--wb', f.body_weight||400);
  const u = Math.min(scene.w, scene.h)/1080;               // 1 个单位 = 短边/1080
  K.u = u; r.setProperty('--u', u+'px');
  r.setProperty('--line', ((st.line&&st.line.width)||3)*u+'px');
  const L = st.layout_rules||{}; K.margin = (L.margin||0.09)*Math.min(scene.w,scene.h);
  K.align = L.align||'center';
  K.speed = (st.motion&&st.motion.speed)||1;               // >1 更快
  K.entrance = (st.motion&&st.motion.entrance)||'rise';
  K.cuts = (st.motion&&st.motion.cuts_per_5s)||2;
  K.textScale = f.scale||1;
  K.background(st.background||{}, scene);
};
K.background = (bg, scene)=>{
  const s = document.getElementById('stage'); s.style.background = 'var(--bg)';
  const tex = bg.texture||'plain', c = bg.texture_color||'rgba(127,127,127,.12)', u=K.u;
  const layer = document.createElement('div'); layer.className='tex';
  if(tex==='grid') layer.style.backgroundImage=`linear-gradient(${c} 1px,transparent 1px),linear-gradient(90deg,${c} 1px,transparent 1px)`, layer.style.backgroundSize=`${60*u}px ${60*u}px`;
  if(tex==='dots') layer.style.backgroundImage=`radial-gradient(${c} ${2*u}px,transparent ${2.4*u}px)`, layer.style.backgroundSize=`${40*u}px ${40*u}px`;
  if(tex==='scanlines') layer.style.backgroundImage=`repeating-linear-gradient(0deg,${c} 0 1px,transparent 1px ${4*u}px)`;
  if(tex==='paper'||tex==='grain') layer.innerHTML=`<svg width="100%" height="100%"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency="${tex==='paper'?0.9:1.6}" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 0.5 0 0 0 0 0.45 0 0 0 0 0.4 0 0 0 ${tex==='paper'?0.10:0.16} 0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`;
  if(tex==='vignette') layer.style.background=`radial-gradient(ellipse at center,transparent 55%,${c} 100%)`;
  s.appendChild(layer);
};

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
  window.LAYOUT.build(stage, sc, st);
  window.KEYTIMES = window.LAYOUT.keyTimes ? window.LAYOUT.keyTimes(sc.dur) : [sc.dur*0.3, sc.dur*0.62, sc.dur-0.04];
  seek(0);
};
})();
