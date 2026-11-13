/* 版式：讲原理 —— 把一句话拆成 2~4 个环节，用线一节一节连起来。
   竖屏从上往下，横屏从左往右。重点环节用强调色。 */
window.LAYOUT = (function(){
  let nodes=[], arrows=[], times=[], dur=3, title=null;
  return {
    build(stage, sc, st){
      dur = sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert = H>W;
      let items = sc.items && sc.items.length ? sc.items : K.chunks(sc.text, vert?4:4);
      if(sc.mode==='anim') items = items.map(s=>K.short(s, 8));
      if(items.length===1 && [...items[0]].length>10) items = K.chunks(items[0].replace(/(是|就是|让|把|会)/,'，$1'),3);
      const n = items.length;
      const emph = sc.emphasis ? items.findIndex(s=>s.includes(sc.emphasis)) : n-1;
      // 每个环节的框
      const gap = (vert?90:110)*u;
      const boxW = vert ? W-2*m : (W-2*m-gap*(n-1))/n;
      const boxH = vert ? Math.min(230*u, (H*0.62-gap*(n-1))/n) : Math.min(300*u, H*0.42);
      const totalH = vert ? n*boxH+(n-1)*gap : boxH;
      const y0 = vert ? (H-totalH)/2 + (sc.mode==='text'?40*u:0) : (H-boxH)/2;
      const svg = K.svg(stage, W, H);
      const lw = getComputedStyle(document.documentElement).getPropertyValue('--line');
      times = K.beats(n, dur);
      nodes = items.map((txt,i)=>{
        const x = vert ? m : m + i*(boxW+gap), y = vert ? y0 + i*(boxH+gap) : y0;
        const r = 26*u;
        const d = `M${x+r},${y} H${x+boxW-r} Q${x+boxW},${y} ${x+boxW},${y+r} V${y+boxH-r} Q${x+boxW},${y+boxH} ${x+boxW-r},${y+boxH} H${x+r} Q${x},${y+boxH} ${x},${y+boxH-r} V${y+r} Q${x},${y} ${x+r},${y} Z`;
        const p = K.path(svg, d, 'box'+(i===emph?' em':'')); p.style.strokeWidth=lw; K.strokeSetup(p);
        const fill = K.path(svg, d, 'fill'+(i===emph?' em':'')); fill.style.opacity=0;
        const badge = K.el('div','badge'+(i===emph?' em':''), String(i+1));
        const bs = 64*u; Object.assign(badge.style,{left:(x+(vert?36*u:boxW/2-bs/2))+'px', top:(y+(vert?boxH/2-bs/2:36*u))+'px', width:bs+'px', height:bs+'px', fontSize:34*u+'px'});
        const lab = K.el('div','lab'+(i===emph?' em':''), K.esc(txt));
        const lx = vert ? x+120*u : x+24*u, lw2 = vert ? boxW-150*u : boxW-48*u;
        const fs = K.fit(txt, lw2, vert?64:58, 30);
        Object.assign(lab.style,{left:lx+'px', width:lw2+'px', top:(vert? y : y+100*u)+'px', height:(vert?boxH:boxH-110*u)+'px', fontSize:fs+'px', textAlign: vert?'left':'center'});
        return {p, fill, badge, lab, t:times[i], em:i===emph};
      });
      arrows = [];
      for(let i=0;i<n-1;i++){
        const a = nodes[i], ax = vert ? W/2 : m + i*(boxW+gap) + boxW + 14*u, ay = vert ? y0 + i*(boxH+gap) + boxH + 14*u : y0+boxH/2;
        const bx = vert ? ax : ax + gap - 28*u, by = vert ? ay + gap - 28*u : ay;
        const head = vert ? `M${bx-16*u},${by-18*u} L${bx},${by} L${bx+16*u},${by-18*u}` : `M${bx-18*u},${by-16*u} L${bx},${by} L${bx-18*u},${by+16*u}`;
        const l = K.path(svg, `M${ax},${ay} L${bx},${by}`, 'arrow'); l.style.strokeWidth=lw; K.strokeSetup(l);
        const h = K.path(svg, head, 'arrow'); h.style.strokeWidth=lw; K.strokeSetup(h);
        arrows.push({l,h,t:(times[i]+times[i+1])/2 - 0.1/K.speed});
      }
      if(sc.mode==='text' && vert){ // 文字多：顶上放一行原话
        title = K.el('div','title', K.esc(sc.text.length>26? sc.text.slice(0,26)+'…' : sc.text));
        Object.assign(title.style,{left:m+'px', width:(W-2*m)+'px', top:(y0-170*u)+'px', fontSize:K.fit(sc.text.slice(0,26), W-2*m, 46, 30)+'px'});
      }
    },
    keyTimes(d){ const last = nodes.length? nodes[nodes.length-1].t : d*0.6; return [Math.min(d*0.35, (nodes[1]||nodes[0]).t+0.35), last+0.4, d-0.04]; },
    seek(t){
      for(const nd of nodes){
        const v = K.enter(t, nd.t, 'draw');
        K.stroke(nd.p, v.draw); nd.fill.style.opacity = (nd.em? 1 : 0.0) * K.eo((t-nd.t-0.25)/0.4);
        const b = K.enter(t, nd.t+0.12/K.speed, 'pop'); K.put(nd.badge, b);
        const l = K.enter(t, nd.t+0.2/K.speed, K.entrance==='draw'?'rise':K.entrance); K.put(nd.lab, l);
      }
      for(const a of arrows){ const p=K.eo((t-a.t)/(0.35/K.speed)); K.stroke(a.l, p); K.stroke(a.h, K.eo((t-a.t-0.25/K.speed)/0.2)); }
      if(title) K.put(title, K.enter(t, 0, 'rise'));
    },
    css: `
      .box{fill:none;stroke:var(--ink);stroke-linejoin:round}
      .box.em{stroke:var(--accent)}
      .fill{fill:none} .fill.em{fill:var(--accent);fill-opacity:.08}
      .arrow{fill:none;stroke:var(--muted);stroke-linecap:round;stroke-linejoin:round}
      .badge{position:absolute;border-radius:50%;border:var(--line) solid var(--ink);color:var(--ink);display:flex;align-items:center;justify-content:center;font-family:var(--font);font-weight:var(--wh);box-sizing:border-box;background:var(--bg)}
      .badge.em{border-color:var(--accent);color:#fff;background:var(--accent)}
      .lab{position:absolute;display:flex;align-items:center;color:var(--ink);font-family:var(--font);font-weight:var(--wb);line-height:1.25;letter-spacing:.02em;justify-content:center}
      .lab:not([style*="center"]){justify-content:flex-start}
      .lab.em{color:var(--accent);font-weight:var(--wh)}
      .title{position:absolute;color:var(--muted);font-family:var(--font);font-weight:var(--wb);line-height:1.3}
    `
  };
})();
