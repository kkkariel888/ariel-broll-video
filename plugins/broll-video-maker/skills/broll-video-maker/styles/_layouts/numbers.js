/* 版式：比数字 —— 句子里有 2 个以上数字就画对比柱，1 个数字就大字滚动，没有数字就放大重点词。
   柱子按真实比例，数字从 0 滚到目标值，最大的那个用强调色。 */
window.LAYOUT = (function(){
  let bars=[], big=null, sub=null, line=null, axis=null, times=[], dur=3, mode='', note=null, noteT=0;
  return {
    build(stage, sc, st){
      dur = sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      const all = K.numbers(sc.text).filter(n=>n.value>0);
      const ratio = all.find(n=>n.unit==='倍');           // 「差 4 倍」是比值，不画成柱子，做成标注
      const nums = all.filter(n=>n!==ratio).slice(0,4);
      const lw = getComputedStyle(document.documentElement).getPropertyValue('--line');
      if(nums.length>=2){
        mode='bars';
        const n=nums.length, max=Math.max(...nums.map(x=>x.value)), names = sc.items&&sc.items.length===n ? sc.items : nums.map(x=>K.labelBefore(sc.text,x)||'');
        times = K.beats(n, dur*0.85);
        const areaW = W-2*m, areaH = vert ? H*0.46 : H*0.5, baseY = vert ? H*0.66 : H*0.72;
        const slot = areaW/n, bw = Math.min(slot*0.56, 260*u);
        const svg = K.svg(stage, W, H);
        axis = K.path(svg, `M${m},${baseY} H${W-m}`, 'axis'); axis.style.strokeWidth=lw; K.strokeSetup(axis);
        bars = nums.map((x,i)=>{
          const cx = m + slot*(i+0.5), h = Math.max(areaH*0.06, areaH*x.value/max), top=x.value===max;
          const b = K.el('div','bar'+(top?' top':'')); Object.assign(b.style,{left:(cx-bw/2)+'px', width:bw+'px', top:(baseY-h)+'px', height:h+'px', transformOrigin:'50% 100%'});
          const v = K.el('div','val'+(top?' top':''), ''); const fs=K.fit('0000', slot*0.95, vert?96:84, 36);
          Object.assign(v.style,{left:(cx-slot/2)+'px', width:slot+'px', top:(baseY-h-fs*1.35)+'px', fontSize:fs+'px'});
          const nm = K.el('div','name', K.esc(sc.mode==='anim'? names[i].slice(0,4) : names[i]));
          Object.assign(nm.style,{left:(cx-slot/2)+'px', width:slot+'px', top:(baseY+22*u)+'px', fontSize:K.fit(names[i]||'名', slot*0.9, 44, 26)+'px'});
          return {b,v,nm,x,t:times[i],top};
        });
        if(ratio){ noteT = times[n-1]+0.7/K.speed; const tx = (K.labelBefore(sc.text,ratio,4)||'差')+' '+ratio.raw.replace(/\s/g,'');
          note = K.el('div','note', K.esc(tx)); const nf=K.fit(tx, W-2*m, vert?84:70, 40);
          Object.assign(note.style,{left:m+'px', width:(W-2*m)+'px', top:(baseY+(vert?150:110)*u)+'px', fontSize:nf+'px'}); }
        if(sc.mode==='text'){ sub = K.el('div','sub', K.esc(sc.text)); Object.assign(sub.style,{left:m+'px', width:(W-2*m)+'px', top:(baseY-areaH-(vert?260:150)*u)+'px', fontSize:K.fit(sc.text.slice(0,22), W-2*m, 50, 30)+'px'}); }
      } else if(nums.length===1){
        mode='big'; const x=nums[0]; times=[0.15/K.speed];
        big = K.el('div','big', ''); big._n=x;
        const fs = K.fit(x.raw+'0', W-2*m, vert?300:260, 120);
        Object.assign(big.style,{left:m+'px', width:(W-2*m)+'px', top:(H/2-fs*0.75)+'px', fontSize:fs+'px'});
        const svg=K.svg(stage,W,H); const ly=H/2+fs*0.55, half=Math.min((W-2*m)/2, fs*1.4);
        line = K.path(svg, `M${W/2-half},${ly} Q${W/2},${ly+18*u} ${W/2+half},${ly-6*u}`, 'uline'); line.style.strokeWidth=`calc(${lw} * 2.2)`; K.strokeSetup(line);
        const rest = (K.labelBefore(sc.text,x,10) || sc.text.replace(x.raw,'').slice(0,12));
        sub = K.el('div','sub center', K.esc(sc.mode==='anim'? K.short(rest,8) : sc.text.length>28? rest : sc.text));
        Object.assign(sub.style,{left:m+'px', width:(W-2*m)+'px', top:(ly+60*u)+'px', fontSize:K.fit(sub.textContent, W-2*m, 56, 30)+'px'});
      } else {
        mode='word'; const cs = K.chunks(sc.text), after = sc.text.split(/[：:]/)[1];
        const w = sc.emphasis || K.short((after && after.trim()) || cs.reduce((a,b)=>b.length>a.length?b:a, cs[0]), 14); times=[0.15/K.speed];
        big = K.el('div','big word', K.esc(w)); const fs=K.fit(w, W-2*m, vert?200:180, 80);
        Object.assign(big.style,{left:m+'px', width:(W-2*m)+'px', top:(H/2-fs*0.75)+'px', fontSize:fs+'px'});
        const svg=K.svg(stage,W,H); const ly=H/2+fs*0.55, half=Math.min((W-2*m)/2, fs*[...w].length/2);
        line = K.path(svg, `M${W/2-half},${ly} H${W/2+half}`, 'uline'); line.style.strokeWidth=`calc(${lw} * 2.2)`; K.strokeSetup(line);
        if(sc.mode==='text'){ sub = K.el('div','sub center', K.esc(sc.text)); Object.assign(sub.style,{left:m+'px', width:(W-2*m)+'px', top:(ly+60*u)+'px', fontSize:K.fit(sc.text.slice(0,22), W-2*m, 50, 30)+'px'}); }
      }
    },
    keyTimes(d){ return mode==='bars' ? [times[0]+0.5, Math.max(times[times.length-1]+0.6, noteT+0.4), d-0.04] : [0.55, d*0.6, d-0.04]; },
    seek(t){
      if(mode==='bars'){
        K.stroke(axis, K.eo(t/(0.4/K.speed)));
        for(const b of bars){
          const k = M.S(t-b.t, 13*K.speed, 0.78); b.b.style.transform=`scaleY(${Math.max(0,k).toFixed(4)})`; b.b.style.opacity = t>=b.t?1:0;
          const p = K.clamp((t-b.t)/(0.9/K.speed)); b.v.textContent = t>=b.t ? K.countText(b.x,p) : ''; K.put(b.v, K.enter(t,b.t,'rise'));
          K.put(b.nm, K.enter(t, b.t-0.05, 'rise'));
        }
      } else {
        const t0=times[0];
        if(mode==='big'){ big.textContent = K.countText(big._n, (t-t0)/(1.1/K.speed)); }
        K.put(big, K.enter(t,t0, K.entrance==='draw'?'pop':K.entrance));
        K.stroke(line, K.eo((t-t0-0.45/K.speed)/(0.5/K.speed)));
      }
      if(note) K.put(note, K.enter(t, noteT, 'pop'));
      if(sub) K.put(sub, K.enter(t, (times[0]||0)+0.55/K.speed, 'rise'));
    },
    css: `
      .axis{fill:none;stroke:var(--muted);stroke-linecap:round}
      .bar{position:absolute;background:var(--muted);opacity:.0;border-radius:calc(var(--u)*14) calc(var(--u)*14) 0 0}
      .bar.top{background:var(--accent)}
      .val,.name,.sub,.big{position:absolute;text-align:center;font-family:var(--font);color:var(--ink)}
      .val{font-weight:var(--wh);font-variant-numeric:tabular-nums;letter-spacing:-.02em}
      .val.top{color:var(--accent)}
      .name{color:var(--muted);font-weight:var(--wb)}
      .sub{color:var(--ink);font-weight:var(--wb);line-height:1.35}
      .big{font-weight:var(--wh);color:var(--accent);line-height:1.1;font-variant-numeric:tabular-nums;letter-spacing:-.03em}
      .big.word{color:var(--ink)}
      .note{position:absolute;text-align:center;font-family:var(--font);font-weight:var(--wh);color:var(--accent2)}
      .uline{fill:none;stroke:var(--accent2);stroke-linecap:round}
    `
  };
})();
