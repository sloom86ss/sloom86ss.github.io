/* SLOOM KORA 365 — shared ScoreBat archive player */
(function(){
  'use strict';
  const root=document.querySelector('#sloom-video-screen .sloom-summary-screen');
  if(!root)return;
  root.innerHTML='<div class="sloom-archive-ui" dir="rtl"><div class="sloom-archive-controls"><label>اختر المباراة<select id="sloomArchiveMatch"><option>جارٍ تحميل الأرشيف…</option></select></label><label>نوع الملخص<select id="sloomArchiveVideo" disabled><option>اختر المباراة أولاً</option></select></label></div><div class="sloom-archive-player" id="sloomArchivePlayer"><span>جارٍ تحميل فيديوهات الملخصات…</span></div><div class="sloom-archive-count" id="sloomArchiveCount"></div></div>';
  const matchSelect=root.querySelector('#sloomArchiveMatch');
  const videoSelect=root.querySelector('#sloomArchiveVideo');
  const player=root.querySelector('#sloomArchivePlayer');
  const count=root.querySelector('#sloomArchiveCount');
  let matches=[];
  function safeEmbed(embed){
    const doc=new DOMParser().parseFromString(String(embed||''),'text/html');
    let src=doc.querySelector('iframe')?.getAttribute('src')||'';
    if(!src && /^https:\/\//i.test(String(embed||'')))src=String(embed);
    try{
      const u=new URL(src);
      const allowed=['scorebat.com','www.scorebat.com','youtube.com','www.youtube.com','youtu.be','vimeo.com','www.dailymotion.com','dailymotion.com'];
      if(u.protocol!=='https:'||!allowed.includes(u.hostname))return '';
      return u.href;
    }catch(e){return ''}
  }
  function showVideo(){
    const m=matches[Number(matchSelect.value)];
    if(!m)return;
    const v=(m.videos||[])[Number(videoSelect.value)];
    const src=safeEmbed(v?.embed);
    player.replaceChildren();
    if(!src){player.textContent='رابط الفيديو غير متاح من المصدر حالياً';return;}
    const frame=document.createElement('iframe');
    frame.src=src;frame.title=(v?.title||'ملخص المباراة')+' — '+(m.title||'');
    frame.allow='autoplay; fullscreen; picture-in-picture';frame.allowFullscreen=true;
    frame.loading='lazy';frame.referrerPolicy='strict-origin-when-cross-origin';
    player.appendChild(frame);
  }
  function fillVideos(){
    const m=matches[Number(matchSelect.value)];
    videoSelect.innerHTML='';
    (m?.videos||[]).forEach((v,i)=>{
      const o=document.createElement('option');o.value=String(i);o.textContent=v.title||('ملخص '+(i+1));videoSelect.appendChild(o);
    });
    videoSelect.disabled=!m?.videos?.length;
    if(m?.videos?.length)showVideo();else player.textContent='لا توجد فيديوهات متاحة لهذه المباراة';
  }
  fetch('./data/scorebat-highlights.json?ts='+Date.now(),{cache:'no-store'})
    .then(r=>{if(!r.ok)throw new Error('archive unavailable');return r.json()})
    .then(data=>{
      matches=Array.isArray(data.response)?data.response:[];
      matches=matches.filter(m=>m&&Array.isArray(m.videos)&&m.videos.length);
      matches.sort((a,b)=>new Date(b.date||0)-new Date(a.date||0));
      matchSelect.innerHTML='';
      matches.forEach((m,i)=>{
        const o=document.createElement('option');o.value=String(i);
        const d=m.date?new Date(m.date):null;
        const date=d&&!Number.isNaN(d.getTime())?' — '+d.toLocaleDateString('ar',{year:'numeric',month:'short',day:'numeric'}):'';
        o.textContent=(m.title||'مباراة')+' — '+(m.competition||'')+date;
        matchSelect.appendChild(o);
      });
      count.textContent='الأرشيف المشترك: '+matches.length+' مباراة';
      if(matches.length){matchSelect.value='0';fillVideos();}
      else player.textContent='سيظهر الأرشيف هنا بعد أول مزامنة للمباريات';
    })
    .catch(()=>{matchSelect.innerHTML='<option>الأرشيف غير متاح حالياً</option>';player.textContent='تعذر تحميل الأرشيف. حاول لاحقاً.'});
  matchSelect.addEventListener('change',fillVideos);
  videoSelect.addEventListener('change',showVideo);
})();