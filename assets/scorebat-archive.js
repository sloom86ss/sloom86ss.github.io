/* SLOOM KORA 365 — shared ScoreBat archive player */
(function(){
  'use strict';
  const root=document.querySelector('#sloom-video-screen .sloom-summary-screen');
  if(!root)return;
  root.innerHTML='<div class="sloom-archive-ui" dir="rtl"><div class="sloom-archive-controls"><label>المباراة الحالية<select id="sloomArchiveMatch"><option>جارٍ تحميل الأرشيف…</option></select></label><label>الملخص<select id="sloomArchiveVideo" disabled><option>جارٍ التحميل</option></select></label></div><div class="sloom-archive-player" id="sloomArchivePlayer"><span>جارٍ تحميل فيديوهات الملخصات…</span></div><div class="sloom-archive-count" id="sloomArchiveCount"></div></div>';
  const matchSelect=root.querySelector('#sloomArchiveMatch');
  const videoSelect=root.querySelector('#sloomArchiveVideo');
  const player=root.querySelector('#sloomArchivePlayer');
  const count=root.querySelector('#sloomArchiveCount');
  let matches=[];
  let playSequence=0;
  let activeFailureHandler=null;

  function getMatchKey(match){
    const id=String(match?.video_id||match?.source_url||'').match(/matchview\/(\d+)/i);
    return id?'match:'+id[1]:[match?.title||'',match?.competition||'',match?.date||''].join('|');
  }

  function getVideoKey(video){
    let src=String(video?.url||'').trim();
    if(!src){
      const embed=String(video?.embed||'');
      const doc=new DOMParser().parseFromString(embed,'text/html');
      src=doc.querySelector('iframe')?.getAttribute('src')||'';
      if(!src && /^https:\/\//i.test(embed))src=embed;
    }
    const path=src.match(/^https:\/\/www?\.scorebat\.com(\/embed\/v\/[^?#]+)/i);
    return path?path[1]:String(video?.title||'');
  }

  function deduplicateMatches(items){
    const grouped=new Map();
    (Array.isArray(items)?items:[]).forEach(item=>{
      if(!item||!Array.isArray(item.videos)||!item.videos.length)return;
      const key=getMatchKey(item);
      if(!grouped.has(key))grouped.set(key,{...item,videos:[]});
      const target=grouped.get(key);
      const videoMap=new Map(target.videos.map(video=>[getVideoKey(video),video]));
      item.videos.forEach(video=>{
        const videoKey=getVideoKey(video);
        if(videoKey)videoMap.set(videoKey,video);
      });
      target.videos=[...videoMap.values()];
      if(item.title)target.title=item.title;
      if(item.competition)target.competition=item.competition;
      if(item.date)target.date=item.date;
      if(item.source_url)target.source_url=item.source_url;
    });
    return [...grouped.values()];
  }

  function getVideoUrl(video){
    let src=String(video?.url||'').trim();
    if(!src){
      const embed=String(video?.embed||'');
      const doc=new DOMParser().parseFromString(embed,'text/html');
      src=doc.querySelector('iframe')?.getAttribute('src')||'';
      if(!src && /^https:\/\//i.test(embed))src=embed;
    }
    try{
      const u=new URL(src);
      if(u.protocol!=='https:'||!['scorebat.com','www.scorebat.com'].includes(u.hostname))return null;
      return u.href;
    }catch(e){return null;}
  }


  function advanceVideo(){
    const matchIndex=Number(matchSelect.value);
    const videoIndex=Number(videoSelect.value);
    const currentMatch=matches[matchIndex];
    if(currentMatch&&videoIndex+1<(currentMatch.videos||[]).length){
      videoSelect.value=String(videoIndex+1);
      showVideo();
      return;
    }
    if(matchIndex+1<matches.length){
      matchSelect.value=String(matchIndex+1);
      fillVideos();
      return;
    }
    count.textContent='انتهت جميع الملخصات المتاحة حالياً';
  }

  function showVideo(){
    const sequence=++playSequence;
    const match=matches[Number(matchSelect.value)];
    if(!match)return;
    const video=(match.videos||[])[Number(videoSelect.value)];
    const url=getVideoUrl(video);
    if(activeFailureHandler){window.removeEventListener('message',activeFailureHandler);activeFailureHandler=null;}
    player.replaceChildren();
    if(!url){player.textContent='رابط الفيديو غير متاح من المصدر حالياً';return;}
    const iframe=document.createElement('iframe');
    iframe.id='sloomArchiveIframe';
    const playerOrigin=new URL(url).origin;
    activeFailureHandler=(event)=>{
      if(event.origin!==playerOrigin||event.source!==iframe.contentWindow)return;
      let message;
      try{message=typeof event.data==='string'?JSON.parse(event.data):event.data;}catch(e){return;}
      if(!message||message.type!=='scorebat-playback-failed')return;
      if(!['provider-error','timeout'].includes(message.reason))return;
      window.removeEventListener('message',activeFailureHandler);
      activeFailureHandler=null;
      if(iframe.isConnected){
        iframe.remove();
        player.textContent='هذا الملخص غير متاح للتشغيل حالياً من المصدر.';
      }
    };
    window.addEventListener('message',activeFailureHandler);
    iframe.src=url;
    iframe.title=video.title||'ملخص المباراة';
    iframe.allow='fullscreen; picture-in-picture';
    iframe.allowFullscreen=true;
    iframe.loading='eager';
    iframe.referrerPolicy='strict-origin-when-cross-origin';
    iframe.style.cssText='width:100%;aspect-ratio:16/9;border:0;display:block';
    player.appendChild(iframe);

  }

  function fillVideos(){
    const match=matches[Number(matchSelect.value)];
    videoSelect.replaceChildren();
    (match?.videos||[]).forEach((video,index)=>{
      const option=document.createElement('option');
      option.value=String(index);
      option.textContent=video.title||('ملخص '+(index+1));
      videoSelect.appendChild(option);
    });
    videoSelect.disabled=!match?.videos?.length;
    if(match?.videos?.length){videoSelect.value='0';showVideo();}
    else player.textContent='لا توجد فيديوهات متاحة لهذه المباراة';
  }

  fetch('./data/scorebat-highlights.json?ts='+Date.now(),{cache:'no-store'})
    .then(response=>{if(!response.ok)throw new Error('archive unavailable');return response.json();})
    .then(data=>{
      matches=deduplicateMatches(data.response);
      matches.sort((a,b)=>new Date(b.date||0)-new Date(a.date||0));
      matchSelect.replaceChildren();
      matches.forEach((match,index)=>{
        const option=document.createElement('option');
        option.value=String(index);
        const date=match.date?new Date(match.date):null;
        const dateText=date&&!Number.isNaN(date.getTime())?' — '+date.toLocaleDateString('ar',{year:'numeric',month:'short',day:'numeric'}):'';
        option.textContent=(match.title||'مباراة')+' — '+(match.competition||'')+dateText;
        matchSelect.appendChild(option);
      });
      count.textContent='أرشيف ScoreBat: '+matches.length+' مباراة متاحة';
      if(matches.length){matchSelect.value='0';fillVideos();}
      else player.textContent='سيظهر الأرشيف هنا بعد أول مزامنة للمباريات';
    })
    .catch(()=>{
      matchSelect.innerHTML='<option>الأرشيف غير متاح حالياً</option>';
      player.textContent='تعذر تحميل الأرشيف. حاول لاحقاً.';
    });

  matchSelect.addEventListener('change',fillVideos);
  videoSelect.addEventListener('change',showVideo);
})();