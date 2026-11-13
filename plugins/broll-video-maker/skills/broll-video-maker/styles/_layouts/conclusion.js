/* 版式：讲结论 —— 小标签「结论」+ 一条短线，然后一句大字一段一段浮上来，最后的重点被强调。 */
window.LAYOUT = (function(){
  let tag=null, bar=null, lines=[], times=[], dur=3, hl=null;
  return {
    build(stage, sc){
      dur=sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      let txt = (sc.text.split(/[：:]/)[1]||sc.text).trim();
      if(sc.mode==='anim') txt = K.short(txt, 18);
      let parts = sc.items&&sc.items.length ? sc.items : K.chunks(txt, 3);
      if(parts.length>1) parts = parts.filter(p=>!/^(所以|总之|说到底|所以说到底|一句话|说白了|记住|结论)$/.test(p)) ;
      parts = parts.map(p=>p.replace(/^(所以|总之|说到底|说白了)+/,''));
      if(parts.length===1 && [...parts[0]].length>(vert?8:12)){ // 在「是 / 就是 / 在于 / 不是」这类自然停顿处断行，找不到再对半
        const s=parts[0], half=s.length/2; let best=-1, bd=1e9; const re=/(就是|在于|不是|是|才是|要|会|能)/g; let mm;
        while((mm=re.exec(s))){ const d=Math.abs(mm.index-half); if(mm.index>1 && d<bd){bd=d;best=mm.index;} }
        const k = best>0 ? best : Math.ceil(half); parts=[s.slice(0,k), s.slice(k)]; }
      const hit = sc.emphasis || parts[parts.length-1];
      const left = K.align==='left' || !vert ? m : m;
      const maxLen = Math.max(...parts.map(p=>[...p].length));
      const fs = K.fit('字'.repeat(maxLen), W-2*m, vert?150:120, 52);
      const blockH = parts.length*fs*1.25, y0 = (H-blockH)/2 + 30*u;
      tag = K.el('div','kick', '结论'); Object.assign(tag.style,{left:left+'px',top:(y0-110*u)+'px',fontSize:32*u+'px'});
      bar = K.el('div','cbar'); Object.assign(bar.style,{left:(left+110*u)+'px',top:(y0-90*u)+'px',width:120*u+'px',height:Math.max(2,3*u)+'px'});
      times = K.beats(parts.length, dur*0.75).map(x=>x+0.25/K.speed);
      lines = parts.map((p,i)=>{ const el=K.el('div','head cline', p===hit? K.mark(p,p) : K.esc(p));
        Object.assign(el.style,{left:left+'px',width:(W-2*m)+'px',top:(y0+i*fs*1.25)+'px',fontSize:fs+'px'}); if(p===hit) hl=el; return {el,t:times[i]}; });
    },
    keyTimes(d){ return [times[0]+0.4, times[times.length-1]+0.8, d-0.04]; },
    seek(t){
      K.put(tag,K.enter(t,0.05,'rise')); bar.style.transform=`scaleX(${K.eio(K.clamp((t-0.15)/0.5)).toFixed(4)})`;
      for(const l of lines) K.put(l.el, K.enter(t,l.t,K.entrance==='type'?'rise':K.entrance));
      if(hl) K.markSeek(hl, K.clamp((t-times[times.length-1]-0.45/K.speed)/(0.5/K.speed)));
    },
    css:`
      .cbar{background:var(--accent);transform-origin:0 50%;transform:scaleX(0)}
      .cline{line-height:1.2;white-space:nowrap}
    `
  };
})();
