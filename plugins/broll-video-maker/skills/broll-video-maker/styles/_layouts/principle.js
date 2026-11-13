/* 版式：讲原理 —— 2~4 个环节，编号 + 卡片 + 一条细线把它们串起来。竖屏上下排，横屏左右排。 */
window.LAYOUT = (function(){
  let cards=[], rails=[], times=[], dur=3, vert=true, title=null;
  return {
    build(stage, sc){
      dur=sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin; vert=H>W;
      let items = sc.items&&sc.items.length ? sc.items : K.chunks(sc.text, 4);
      if(items.length===1 && [...items[0]].length>10) items = K.chunks(items[0].replace(/(是|就是|让|把|会)/,'，$1'),3);
      if(sc.mode==='anim') items = items.map(s=>K.short(s,9));
      const n=items.length, emph = sc.emphasis ? Math.max(0,items.findIndex(s=>s.includes(sc.emphasis))) : n-1;
      times = K.beats(n, dur);
      const gap=(vert?46:40)*u, cw = vert ? W-2*m : (W-2*m-gap*(n-1))/n;
      const ch = vert ? Math.min(300*u,(H*0.66-gap*(n-1))/n) : Math.min(360*u, H*0.5);
      const total = vert ? n*ch+(n-1)*gap : ch, y0 = (H-total)/2 + (vert&&sc.mode==='text'?60*u:0);
      rails = [];
      for(let i=0;i<n-1;i++){ const r=K.el('div','rail'); const f=K.el('div','railfill','',r); const lw=Math.max(2,2*u);
        if(vert) Object.assign(r.style,{left:(m+cw/2-lw/2)+'px', top:(y0+(i+1)*ch+i*gap)+'px', width:lw+'px', height:gap+'px'});
        else Object.assign(r.style,{left:(m+(i+1)*cw+i*gap)+'px', top:(y0+ch/2-lw/2)+'px', height:lw+'px', width:gap+'px'});
        rails.push({f, t0:times[i]+0.2/K.speed, t1:times[i+1]}); }
      cards = items.map((txt,i)=>{
        const x = vert? m : m+i*(cw+gap), y = vert? y0+i*(ch+gap) : y0;
        const c = K.surf(K.el('div','pcard'+(i===emph?' em':'')));
        Object.assign(c.style,{left:x+'px',top:y+'px',width:cw+'px',height:ch+'px', padding: vert?`0 ${44*u}px 0 ${130*u}px`:`${36*u}px ${30*u}px`});
        const no = K.el('div','kick pno', String(i+1).padStart(2,'0'), c); no.style.fontSize=30*u+'px';
        if(vert) Object.assign(no.style,{position:'absolute',left:(40*u)+'px',top:'50%',transform:'translateY(-50%)'});
        const tx = K.el('div','head ptx', i===emph&&sc.emphasis? K.mark(txt, sc.emphasis) : K.esc(txt), c);
        const avail = vert? cw-180*u : cw-60*u;
        tx.style.fontSize = K.fit(txt, avail, vert?88:68, 34)+'px'; if(!vert){tx.style.marginTop=18*u+'px'; tx.style.textAlign='center';}
        return {c, t:times[i], em:i===emph, tx};
      });
      if(sc.mode==='text'){ title = K.el('div','body mut', K.esc(sc.text)); Object.assign(title.style,{left:m+'px',width:(W-2*m)+'px',top:(y0-(vert?150:110)*u)+'px',fontSize:K.fit(sc.text.slice(0,24),W-2*m,40,26)+'px',textAlign:vert?'left':'center',lineHeight:1.4}); }
    },
    keyTimes(d){ const L=cards[cards.length-1].t; return [Math.min(d*0.4,(cards[1]||cards[0]).t+0.4), L+0.55, d-0.04]; },
    seek(t){
      for(const r of rails){ const p=K.eio(K.clamp((t-r.t0)/Math.max(0.15,r.t1-r.t0))); r.f.style.transform = vert?`scaleY(${p})`:`scaleX(${p})`; }
      for(const c of cards){ K.put(c.c, K.enter(t,c.t)); c.c.classList.toggle('on', t>=c.t+0.25/K.speed && c.em); K.markSeek(c.tx, K.clamp((t-c.t-0.35/K.speed)/0.45)); }
      if(title) K.put(title, K.enter(t,0,'rise'));
    },
    css:`
      .rail{background:color-mix(in srgb,var(--line-c) 35%,transparent);overflow:hidden}
      .railfill{width:100%;height:100%;background:var(--accent);transform-origin:0 0}
      .pcard{display:flex;align-items:center;flex-direction:column;justify-content:center;align-items:flex-start}
      .pcard .ptx{line-height:1.22}
      .pcard.em{border-color:var(--accent)}
      .pcard.em.on .ptx{color:var(--accent)}
      .pno{opacity:.9}
    `
  };
})();
