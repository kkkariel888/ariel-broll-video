/* 版式：讲新闻 —— 一张标题卡：顶上小标签（日期/快讯），大标题，关键词用荧光笔划出来，底下一条细线 + 一句补充。 */
window.LAYOUT = (function(){
  let card=null, tag=null, hd=null, rule=null, sub=null, t0=0.1, dur=3;
  return {
    build(stage, sc){
      dur=sc.dur; const u=K.u, W=sc.w, H=sc.h, m=K.margin, vert=H>W;
      const date = (sc.text.match(/\d{1,2}\s*月\s*\d{1,2}\s*日|今天|昨天|刚刚|本周|今年/)||[])[0] || '快讯';
      const cs = K.chunks(sc.text,3); let head = cs[0], rest = cs.slice(1).join('，');
      if(sc.mode==='anim'){ head=K.short(head,16); rest=rest?K.short(rest,14):''; }
      const hit = sc.emphasis || (head.match(/[A-Za-z0-9.]+[一-龥]{0,2}|发布|上线|宣布|官宣|暴跌|暴涨|降价|涨价/)||[])[0] || head.slice(-Math.min(4,head.length));
      const cw = vert ? W-2*m : Math.min(W-2*m, 1500*u);
      card = K.surf(K.el('div','ncard')); Object.assign(card.style,{left:((W-cw)/2)+'px',width:cw+'px',padding:`${64*u}px ${60*u}px ${66*u}px`});
      tag = K.el('div','kick ntag', K.esc(date), card); tag.style.fontSize=32*u+'px';
      hd = K.el('div','head nhd', K.mark(head, hit), card); hd.style.fontSize=K.fit(head.slice(0,8), cw-120*u, vert?120:96, 48)+'px'; hd.style.marginTop=26*u+'px';
      rule = K.el('div','nrule','',card); rule.style.marginTop=40*u+'px'; rule.style.height=Math.max(1,2*u)+'px';
      if(rest){ sub = K.el('div','body mut nsub', K.esc(rest), card); sub.style.fontSize=K.fit(rest.slice(0,14), cw-120*u, 52, 28)+'px'; sub.style.marginTop=30*u+'px'; }
      card.style.top=((H-card.offsetHeight)/2)+'px';
    },
    keyTimes(d){ return [0.5, Math.min(d-0.3, 1.6/K.speed), d-0.04]; },
    seek(t){
      K.put(card, K.enter(t,t0,'rise')); K.put(tag, K.enter(t,t0+0.15,'rise')); K.put(hd, K.enter(t,t0+0.25,'rise'));
      K.markSeek(hd, K.clamp((t-t0-0.75/K.speed)/(0.5/K.speed)));
      rule.style.transform=`scaleX(${K.eio(K.clamp((t-t0-0.9/K.speed)/0.5)).toFixed(4)})`;
      if(sub) K.put(sub, K.enter(t,t0+1.1/K.speed,'rise'));
    },
    css:`
      .nhd{line-height:1.22}
      .nrule{background:var(--line-c);opacity:.5;transform-origin:0 50%;transform:scaleX(0)}
      .nsub{line-height:1.45}
    `
  };
})();
