/* 版式：演示工具 —— 一个窗口，光标把这句话一个字一个字打出来，
   回车后一条条输出结果并打勾，最后进度条走满。 */
window.LAYOUT = (function(){
  let win=null, cmd=null, caret=null, outs=[], bar=null, fillEl=null, typeT0=0, typeT1=0, text='', dur=3;
  return {
    build(stage, sc, st){
      dur = sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      let items = sc.items && sc.items.length ? sc.items : K.chunks(sc.text, 3);
      text = sc.mode==='anim' ? K.short(items[0], 14) : (sc.text.length>40 ? sc.text.slice(0,40)+'…' : sc.text);
      const outsTxt0 = (items.length>1 ? items.slice(1) : [K.short(sc.text,10)]).map(s=>sc.mode==='anim'?K.short(s,10):s).slice(0,3);
      const outsTxt = outsTxt0;
      const ww = W-2*m, wh = vert ? Math.min(H*0.56, 980*u) : H*0.7;
      win = K.el('div','win'); Object.assign(win.style,{left:m+'px', width:ww+'px'});
      const head = K.el('div','head','<i></i><i></i><i></i><span>~/broll</span>', win); head.style.height=64*u+'px';
      const body = K.el('div','body','',win); body.style.padding=`${48*u}px ${48*u}px ${56*u}px`;
      const fs = K.fit(text, ww-96*u, vert?64:52, 32);
      const line = K.el('div','cmdline','<b>›</b> ',body); line.style.fontSize=fs+'px';
      cmd = K.el('span','cmd','',line); caret = K.el('span','caret','',line); caret.style.height=fs*1.05+'px'; caret.style.width=fs*0.5+'px';
      typeT0 = 0.25/K.speed; const cps = 16*K.speed; typeT1 = typeT0 + [...text].length/cps;
      typeT1 = Math.min(typeT1, dur*0.45);
      const ot = K.beats(outsTxt.length, Math.max(0.6, dur - typeT1)).map(x=>x+typeT1+0.15);
      outs = outsTxt.map((s,i)=>{ const o = K.el('div','out','<em>✓</em> '+K.esc(s), body); o.style.fontSize=fs*0.86+'px'; o.style.marginTop=26*u+'px'; return {o,t:ot[i]}; });
      bar = K.el('div','pbar','',body); bar.style.height=14*u+'px'; bar.style.marginTop=40*u+'px';
      fillEl = K.el('div','pfill','',bar);
      win.style.top = ((H-win.offsetHeight)/2)+'px';   // 窗口高度跟内容走，居中
    },
    keyTimes(d){ return [typeT1*0.6, (outs[0]?outs[0].t:typeT1)+0.4, d-0.04]; },
    seek(t){
      K.put(win, K.enter(t, 0, 'pop'));
      const chars=[...text]; const n = Math.round(chars.length*K.clamp((t-typeT0)/(typeT1-typeT0)));
      M.setText(cmd, chars.slice(0,n).join(''));
      const typing = t<typeT1+0.1; caret.style.opacity = typing ? 1 : (Math.floor(t*2.4)%2?0:1);
      for(const o of outs) K.put(o.o, K.enter(t, o.t, 'rise'));
      const p = K.clamp((t-typeT1)/Math.max(0.3, dur-typeT1-0.35)); fillEl.style.width=(K.eio(p)*100).toFixed(2)+'%';
    },
    css: `
      .win{position:absolute;background:var(--panel);border-radius:calc(var(--u)*22);overflow:hidden;box-shadow:0 calc(var(--u)*30) calc(var(--u)*80) rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.08)}
      .head{display:flex;align-items:center;gap:calc(var(--u)*14);padding:0 calc(var(--u)*26);background:rgba(255,255,255,.04);border-bottom:1px solid rgba(255,255,255,.06)}
      .head i{width:calc(var(--u)*18);height:calc(var(--u)*18);border-radius:50%;background:var(--muted);opacity:.5}
      .head i:first-child{background:var(--accent);opacity:.9}
      .head span{margin-left:auto;color:var(--muted);font-family:var(--mono);font-size:calc(var(--u)*24)}
      .body{font-family:var(--mono);color:var(--ink)}
      .cmdline b{color:var(--accent);font-weight:700}
      .cmd{white-space:pre-wrap;word-break:break-all;line-height:1.4}
      .caret{display:inline-block;background:var(--accent);vertical-align:text-bottom;margin-left:calc(var(--u)*4)}
      .out{color:var(--ink);opacity:0;line-height:1.35}
      .out em{font-style:normal;color:var(--accent2);font-weight:700}
      .pbar{background:rgba(255,255,255,.08);border-radius:99px;overflow:hidden}
      .pfill{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:99px}
    `
  };
})();
