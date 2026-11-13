/* 版式：比数字 —— 2 个以上数字画对比柱；1 个数字大字滚动；「差 N 倍」做成胶囊标注。 */
window.LAYOUT = (function(){
  let bars=[], big=null, lab=null, sub=null, note=null, base=null, times=[], dur=3, mode='', noteT=0;
  return {
    build(stage, sc){
      dur=sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      const all=K.numbers(sc.text).filter(n=>n.value>0), ratio=all.find(n=>n.unit==='倍'), nums=all.filter(n=>n!==ratio).slice(0,4);
      if(nums.length>=2){
        mode='bars'; const n=nums.length, max=Math.max(...nums.map(x=>x.value));
        const names = sc.items&&sc.items.length===n ? sc.items : nums.map(x=>K.labelBefore(sc.text,x)||'');
        times = K.beats(n, dur*0.8);
        const areaH = vert?H*0.48:H*0.5, baseY = vert?H*0.68:H*0.72, slot=(W-2*m)/n, bw=Math.min(slot*0.46, 230*u);
        base = K.el('div','nbase'); Object.assign(base.style,{left:m+'px',top:baseY+'px',width:(W-2*m)+'px',height:Math.max(1,1.5*u)+'px'});
        bars = nums.map((x,i)=>{
          const cx=m+slot*(i+0.5), h=Math.max(areaH*0.05, areaH*x.value/max), top=x.value===max;
          const b=K.el('div','nbar'+(top?' top':'')); Object.assign(b.style,{left:(cx-bw/2)+'px',width:bw+'px',top:(baseY-h)+'px',height:h+'px'});
          const fs=K.fit('0000',slot*0.95,vert?150:110,40);
          const v=K.el('div','head nval'+(top?' top':'')); Object.assign(v.style,{left:(cx-slot/2)+'px',width:slot+'px',top:(baseY-h-fs*1.3)+'px',fontSize:fs+'px'});
          const nm=K.el('div','body mut nname', K.esc(sc.mode==='anim'?names[i].slice(0,5):names[i]));
          Object.assign(nm.style,{left:(cx-slot/2)+'px',width:slot+'px',top:(baseY+24*u)+'px',fontSize:K.fit(names[i]||'名',slot*0.9,46,26)+'px'});
          return {b,v,nm,x,t:times[i]};
        });
        if(ratio){ noteT=times[n-1]+0.7/K.speed; const tx=(K.labelBefore(sc.text,ratio,4)||'差')+' '+ratio.raw.replace(/\s/g,'');
          note=K.surf(K.el('div','head nnote',K.esc(tx))); const nf=K.fit(tx,W*0.6,vert?76:60,32);
          Object.assign(note.style,{fontSize:nf+'px',top:(baseY+(vert?130:96)*u)+'px',left:'50%',padding:`${nf*0.32}px ${nf*0.8}px`}); note._c=true; }
        if(sc.mode==='text'){ sub=K.el('div','body',K.esc(sc.text)); Object.assign(sub.style,{left:m+'px',width:(W-2*m)+'px',top:(baseY-areaH-(vert?230:140)*u)+'px',fontSize:K.fit(sc.text.slice(0,22),W-2*m,44,26)+'px',textAlign:'center',lineHeight:1.4}); }
      } else {
        mode='big'; const x=nums[0]||ratio; times=[0.15/K.speed];
        const fs=K.fit(x.raw+'00',W-2*m,vert?320:280,120);
        lab=K.el('div','kick', K.esc(K.labelBefore(sc.text,x,8)||'数字')); Object.assign(lab.style,{left:m+'px',width:(W-2*m)+'px',top:(H/2-fs*0.95)+'px',fontSize:28*u+'px',textAlign:'center'});
        big=K.el('div','head nbig'); big._n=x; Object.assign(big.style,{left:m+'px',width:(W-2*m)+'px',top:(H/2-fs*0.6)+'px',fontSize:fs+'px'});
        const rest = sc.text.slice(x.index+x.raw.length).replace(/^[，,。\s]+/,'') || sc.text;
        const st = sc.mode==='anim'? K.short(rest,12) : rest;
        sub=K.el('div','body mut',K.esc(st)); Object.assign(sub.style,{left:m+'px',width:(W-2*m)+'px',top:(H/2+fs*0.62)+'px',fontSize:K.fit(st,W-2*m,50,28)+'px',textAlign:'center',lineHeight:1.4});
      }
    },
    keyTimes(d){ return mode==='bars'?[times[0]+0.5, Math.max(times[times.length-1]+0.7, noteT+0.45), d-0.04]:[0.6,d*0.6,d-0.04]; },
    seek(t){
      if(mode==='bars'){
        base.style.transform=`scaleX(${K.eo(t/(0.5/K.speed)).toFixed(4)})`;
        for(const b of bars){ const k=M.S(t-b.t,12*K.speed,0.82); b.b.style.transform=`scaleY(${Math.max(0,k).toFixed(4)})`; b.b.style.opacity=t>=b.t?1:0;
          b.v.textContent = t>=b.t ? K.countText(b.x, K.clamp((t-b.t)/(0.9/K.speed))) : ''; K.put(b.v,K.enter(t,b.t,'rise')); K.put(b.nm,K.enter(t,b.t-0.05,'rise')); }
        if(note){ const v=K.enter(t,noteT,'pop'); K.put(note,v); note.style.transform+=' translateX(-50%)'; }
      } else {
        big.textContent=K.countText(big._n,(t-times[0])/(1.1/K.speed)); K.put(big,K.enter(t,times[0],'rise'));
        K.put(lab,K.enter(t,times[0]+0.1,'rise'));
      }
      if(sub) K.put(sub,K.enter(t,(times[0]||0)+0.5/K.speed,'rise'));
    },
    css:`
      .nbase{background:var(--line-c);opacity:.55;transform-origin:0 50%}
      .nbar{background:color-mix(in srgb,var(--muted) 60%,transparent);border-radius:calc(var(--u)*12) calc(var(--u)*12) 0 0;transform-origin:50% 100%;opacity:0}
      .nbar.top{background:var(--accent)}
      .nval{text-align:center;font-variant-numeric:tabular-nums;line-height:1}
      .nval.top{color:var(--accent)}
      .nname{text-align:center}
      .nnote{position:absolute;color:var(--accent);white-space:nowrap;border-radius:999px}
      .nbig{text-align:center;color:var(--accent);line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.04em}
    `
  };
})();
