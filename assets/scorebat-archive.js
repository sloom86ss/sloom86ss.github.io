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
  let youtubePlayer=null;
  let playSequence=0;

  function isYouTube(host){
    return ['youtube.com','www.youtube.com','youtu.be','youtube-nocookie.com','www.youtube-nocookie.com'].includes(host);
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
      const allowed=['scorebat.com','www.scorebat.com','youtube.com','www.youtube.com','youtu.be','youtube-nocookie.com','www.youtube-nocookie.com','vimeo.com','player.vimeo.com','www.dailymotion.com','dailymotion.com'];
      if(u.protocol!=='https:'||!allowed.includes(u.hostname))return null;
      u.searchParams.set('autoplay','1');
      if(isYouTube(u.hostname)){
        u.searchParams.set('mute','1');
        u.searchParams.set('enablejsapi','1');
        u.searchParams.set('playsinline','1');
        u.searchParams.set('origin',location.origin);
      }
      return u.href;
    }catch(e){return null;}
  }

  function loadYouTubeApi(){
    if(window.YT&&window.YT.Player)return Promise.resolve();
    if(window.sloomYouTubeApiPromise)return window.sloomYouTubeApiPromise;
    window.sloomYouTubeApiPromise=new Promise(resolve=>{
      const previous=window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady=function(){
        if(typeof previous==='function')previous();
        resolve();
      };
      if(!document.querySelector('script[src="https://www.youtube.com/iframe_api"]')){
        const script=document.createElement('script');
        script.src='https://www.youtube.com/iframe_api';
        document.head.appendChild(script);
      }
    });
    return window.sloomYouTubeApiPromise;
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
    if(youtubePlayer&&typeof youtubePlayer.destroy==='function'){
      try{youtubePlayer.destroy();}catch(e){}
      youtubePlayer=null;
    }
    const match=matches[Number(matchSelect.value)];
    if(!match)return;
    const video=(match.videos||[])[Number(videoSelect.value)];
    const url=getVideoUrl(video);
    player.replaceChildren();
    if(!url){player.textContent='رابط الفيديو غير متاح من المصدر حالياً';return;}
    const iframe=document.createElement('iframe');
    iframe.id='sloomArchiveIframe';
    iframe.src=url;
    iframe.title=video.title||'ملخص المباراة';
    iframe.allow='autoplay; fullscreen; picture-in-picture';
    iframe.allowFullscreen=true;
    iframe.loading='eager';
    iframe.referrerPolicy='strict-origin-when-cross-origin';
    iframe.style.cssText='width:100%;aspect-ratio:16/9;border:0;display:block';
    player.appendChild(iframe);
    const host=new URL(url).hostname;
    if(isYouTube(host)){
      loadYouTubeApi().then(()=>{
        if(sequence!==playSequence||!iframe.isConnected)return;
        youtubePlayer=new YT.Player(iframe,{events:{
          onReady:event=>{try{event.target.mute();event.target.playVideo();}catch(e){}},
          onStateChange:event=>{if(event.data===YT.PlayerState.ENDED&&sequence===playSequence)advanceVideo();}
        }});
      }).catch(()=>{});
    }
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
      matches=Array.isArray(data.response)?data.response:[];
      matches=matches.filter(match=>match&&Array.isArray(match.videos)&&match.videos.length);
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
      count.textContent='الأرشيف المشترك: '+matches.length+' مباراة — التشغيل التلقائي مفعّل';
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