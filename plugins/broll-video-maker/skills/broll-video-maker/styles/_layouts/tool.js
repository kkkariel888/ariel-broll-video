/* 版式：演示工具 —— 一个窗口，光标把话打出来，回车后一行行打勾，进度条走满。 */
window.LAYOUT = (function(){
  let win=null, cmd=null, caret=null, outs=[], fillEl=null, t0=0, t1=0, text='', dur=3;
  return {
    build(stage, sc){
      dur=sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      const items = sc.items&&sc.items.length ? sc.items : K.chunks(sc.text,3);
      text = sc.mode==='anim' ? K.short(items[0],16) : (sc.text.length>40?sc.text.slice(0,40)+'…':sc.text);
      const outsTxt=(items.length>1?items.slice(1):[K.short(sc.text,10)]).map(s=>sc.mode==='anim'?K.short(s,12):s).slice(0,3);
      const ww = vert ? W-2*m : Math.min(W-2*m, 1400*u);
      win = K.surf(K.el('div','twin')); Object.assign(win.style,{left:((W-ww)/2)+'px',width:ww+'px'});
      const hd=K.el('div','thead','<i></i><i></i><i></i>',win); hd.style.height=60*u+'px';
      const body=K.el('div','tbody','',win); body.style.padding=`${50*u}px ${52*u}px ${58*u}px`;
      const fs=K.fit(text, ww-110*u, vert?74:56, 32);
      const line=K.el('div','tline','<b>›</b> ',body); line.style.fontSize=fs+'px';
      cmd=K.el('span','tcmd','',line); caret=K.el('span','tcaret','',line); caret.style.height=fs*1.05+'px'; caret.style.width=fs*0.48+'px';
      t0=0.3/K.speed; t1=Math.min(t0+[...text].length/(16*K.speed), dur*0.45);
      const ot=K.beats(outsTxt.length, Math.max(0.6,dur-t1)).map(x=>x+t1+0.15);
      outs=outsTxt.map((s,i)=>{const o=K.el('div','tout','<em>✓</em><span>'+K.esc(s)+'</span>',body); o.style.fontSize=fs*0.82+'px'; o.style.marginTop=28*u+'px'; return {o,t:ot[i]};});
      const bar=K.el('div','tbar','',body); bar.style.height=10*u+'px'; bar.style.marginTop=44*u+'px'; fillEl=K.el('div','tfill','',bar);
      win.style.top=((H-win.offsetHeight)/2)+'px';
    },
    keyTimes(d){ return [t1*0.7,(outs[0]?outs[0].t:t1)+0.45,d-0.04]; },
    seek(t){
      K.put(win,K.enter(t,0,'pop'));
      const ch=[...text], n=Math.round(ch.length*K.clamp((t-t0)/Math.max(0.01,t1-t0))); M.setText(cmd,ch.slice(0,n).join(''));
      caret.style.opacity = t<t1+0.1 ? 1 : (Math.floor(t*2.4)%2?0:1);
      for(const o of outs) K.put(o.o,K.enter(t,o.t,'rise'));
      fillEl.style.transform=`scaleX(${K.eio(K.clamp((t-t1)/Math.max(0.3,dur-t1-0.35))).toFixed(4)})`;
    },
    css:`
      .twin{overflow:hidden}
      .thead{display:flex;align-items:center;gap:calc(var(--u)*12);padding:0 calc(var(--u)*26);border-bottom:1px solid color-mix(in srgb,var(--line-c) 30%,transparent)}
      .thead i{width:calc(var(--u)*14);height:calc(var(--u)*14);border-radius:50%;background:var(--muted);opacity:.45}
      .thead i:first-child{background:var(--accent);opacity:1}
      .tbody{font-family:var(--mono);color:var(--ink)}
      .tline b{color:var(--accent)}
      .tcmd{white-space:pre-wrap;line-height:1.45;letter-spacing:.01em}
      .tcaret{display:inline-block;background:var(--accent);vertical-align:text-bottom;margin-left:calc(var(--u)*4);border-radius:2px}
      .tout{display:flex;gap:.55em;align-items:baseline;opacity:0;font-family:var(--font);color:var(--ink)}
      .tout em{font-style:normal;color:var(--accent);font-weight:700}
      .tbar{background:color-mix(in srgb,var(--line-c) 22%,transparent);border-radius:99px;overflow:hidden}
      .tfill{height:100%;background:var(--accent);transform-origin:0 50%;transform:scaleX(0)}
    `
  };
})();
