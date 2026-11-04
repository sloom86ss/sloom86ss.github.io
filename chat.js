(()=>{'use strict';
const css=`
#sloom-chat-launch{position:fixed;z-index:2147483647;right:14px;left:auto;bottom:calc(env(safe-area-inset-bottom,0px) + 88px);width:52px;height:52px;display:grid;place-items:center;border:1px solid #d8ff8b;border-radius:50%;padding:0;background:#b7f34a;color:#10170b;font:900 23px Cairo,Arial,sans-serif;box-shadow:0 7px 22px #0009;cursor:pointer;animation:sloomChatFloat 3.2s ease-in-out infinite;touch-action:manipulation} @keyframes sloomChatFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-9px)}} #sloom-chat-launch:active{transform:scale(.94)} @media(prefers-reduced-motion:reduce){#sloom-chat-launch{animation:none}}
#sloom-chat{position:fixed;z-index:2147483647;right:14px;left:auto;bottom:calc(env(safe-area-inset-bottom,0px) + 150px);width:min(370px,calc(100vw - 28px));height:min(540px,calc(100dvh - 125px - env(safe-area-inset-bottom,0px)));display:none;flex-direction:column;overflow:hidden;border:1px solid #526b3a;border-radius:20px;background:#101914;color:#f4f8f4;box-shadow:0 18px 65px #000b;font-family:Cairo,Arial,sans-serif;direction:rtl}
#sloom-chat.open{display:flex}#sloom-chat-head{display:flex;align-items:center;justify-content:space-between;padding:13px 15px;background:#1b3020;border-bottom:1px solid #344b32}
#sloom-chat-head strong{font-size:14px}#sloom-chat-head small{display:block;color:#c2d2c4;font-size:10px}
#sloom-chat-close{border:1px solid #53684b;background:#142018;color:white;border-radius:9px;padding:5px 10px;font-size:18px}
#sloom-chat-log{flex:1;overflow:auto;padding:13px;display:flex;flex-direction:column;gap:10px}
.sloom-msg{max-width:90%;padding:9px 12px;border-radius:14px;font-size:12px;line-height:1.9;white-space:pre-wrap;overflow-wrap:anywhere}
.sloom-msg.bot{align-self:flex-start;background:#1b2a1d;border:1px solid #344b32}.sloom-msg.user{align-self:flex-end;background:#b7f34a;color:#10170b}
#sloom-chat-captcha{padding:6px 10px;background:#111915;min-height:0}#sloom-chat-form{display:flex;gap:7px;padding:10px;border-top:1px solid #26352b;background:#111915}
#sloom-chat-input{min-width:0;flex:1;background:#080c0a;color:#fff;border:1px solid #40523f;border-radius:11px;padding:10px;font:12px Cairo;outline-offset:2px}
#sloom-chat-send{background:#b7f34a;color:#10170b;border:0;border-radius:11px;padding:0 14px;font:800 12px Cairo}
#sloom-chat-note{padding:0 12px 8px;color:#91a095;font-size:9px;background:#111915}
`;
const style=document.createElement('style');style.textContent=css;document.head.appendChild(style);
const launch=document.createElement('button');launch.id='sloom-chat-launch';launch.type='button';launch.textContent='💬';launch.setAttribute('aria-label','افتح مساعد SLOOM الذكي');launch.title='مساعد SLOOM365';
const panel=document.createElement('section');panel.id='sloom-chat';panel.setAttribute('aria-label','مساعد SLOOM365');panel.setAttribute('aria-live','polite');
const head=document.createElement('div');head.id='sloom-chat-head';
const heading=document.createElement('div');const strong=document.createElement('strong');strong.textContent='مساعد SLOOM365';const small=document.createElement('small');small.textContent='مساعد مجاني لكرة القدم من بيانات الموقع';heading.append(strong,small);
const close=document.createElement('button');close.id='sloom-chat-close';close.type='button';close.setAttribute('aria-label','إغلاق المحادثة');close.textContent='×';head.append(heading,close);
const log=document.createElement('div');log.id='sloom-chat-log';
const captchaBox=document.createElement('div');captchaBox.id='sloom-chat-captcha';
const form=document.createElement('form');form.id='sloom-chat-form';
const input=document.createElement('input');input.id='sloom-chat-input';input.maxLength=300;input.autocomplete='off';input.placeholder='اسأل عن مباراة أو نتيجة أو خبر…';input.setAttribute('aria-label','اكتب سؤالك');
const send=document.createElement('button');send.id='sloom-chat-send';send.type='submit';send.textContent='إرسال';form.append(input,send);
const note=document.createElement('div');note.id='sloom-chat-note';note.textContent='مساعد كرة قدم مجاني من بيانات الموقع؛ الذكاء الاصطناعي المتقدم يحتاج تفعيل الخدمة على الخادم.';
panel.append(head,log,captchaBox,form,note);document.body.append(launch,panel);
let cache=null,cacheAt=0,requests=[],turnstileSiteKey='',turnstileToken='',turnstileWidget=null;
function add(text,who){const b=document.createElement('div');b.className='sloom-msg '+who;b.textContent=text;log.appendChild(b);log.scrollTop=log.scrollHeight}
function normalize(s){return String(s||'').toLowerCase().normalize('NFD').replace(/[\u064B-\u065F\u0670]/g,'').replace(/[أإآ]/g,'ا').replace(/ة/g,'ه').replace(/ى/g,'ي')}
function teamAr(n){const map={'Liverpool':'ليفربول','Arsenal':'أرسنال','Manchester City':'مانشستر سيتي','Manchester United':'مانشستر يونايتد','Chelsea':'تشيلسي','Tottenham Hotspur':'توتنهام','Real Madrid':'ريال مدريد','Barcelona':'برشلونة','Bayern Munich':'بايرن ميونخ','Inter':'إنتر ميلان','AC Milan':'ميلان','Juventus':'يوفنتوس','Paris Saint-Germain':'باريس سان جيرمان','Al Hilal':'الهلال','Al Nassr':'النصر','Al Ittihad':'الاتحاد','Al Ahli':'الأهلي'};return map[n]||n||'غير معروف'}
async function getData(){if(cache&&Date.now()-cacheAt<45000)return cache;const r=await fetch('/data.json?chat='+Date.now(),{cache:'no-store'});if(!r.ok)throw Error('تعذر جلب البيانات');const d=await r.json();if(!d||!d.leagues||typeof d.leagues!=='object')throw Error('صيغة بيانات غير صحيحة');cache=d;cacheAt=Date.now();return d}
function remoteContext(d){
 const cleanNews=n=>({headline:String(n.headline||'').slice(0,180),description:String(n.description||'').slice(0,240),published:n.published||'',source:String(n.source||'').slice(0,60),link:String(n.link||'').slice(0,240)});
 const leagues=Object.entries(d.leagues||{}).filter(([,l])=>!l.stale).slice(0,16).map(([key,l])=>({
  name:l.name||key,updated_at:l.updated_at||'',stale:!!l.stale,
  matches:(l.matches||[]).slice(0,5).map(m=>({date:m.date||m.time||'',status:m.status||'',detail:m.detail||'',home:{name:m.home?.name||'',score:m.home?.score??''},away:{name:m.away?.name||'',score:m.away?.score??''}})),
  standings:(l.standings||[]).slice(0,6).map(x=>({name:x.name||x.team?.name||'',points:x.points??'',rank:x.rank??x.position??''})),
  news:(l.news||[]).slice(0,2).map(cleanNews)
 }));
 return {generated_at:d.generated_at||'',provider:d.provider||'',timezone:'Asia/Muscat',news_sources:(d.news_sources||[]).slice(0,6).map(cleanNews),leagues};
}
function fresh(d){const t=Date.parse(d.generated_at||'');return Number.isFinite(t)&&Date.now()-t>=0&&Date.now()-t<90*60*1000&&t<=Date.now()+5*60*1000}
function formatDate(v){const d=new Date(v);return Number.isNaN(d.getTime())?'موعد غير متاح':new Intl.DateTimeFormat('ar-OM',{timeZone:'Asia/Muscat',weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}).format(d)+' بتوقيت عُمان'}
function allMatches(d){const now=Date.now();return Object.entries(d.leagues).filter(([,l])=>{const t=Date.parse(l.updated_at||'');return !l.stale&&Number.isFinite(t)&&now-t>=0&&now-t<=90*60*1000}).flatMap(([key,l])=>(l.matches||[]).map(m=>({...m,league:l.name||key})))}
function answer(q,d){if(!fresh(d))return 'لا أستطيع تأكيد معلومات المباريات الآن لأن آخر تحديث للبيانات قديم أو غير مكتمل. حاول لاحقاً أو راجع المصدر الرسمي.';
const nq=normalize(q),matches=allMatches(d),news=Object.values(d.leagues).flatMap(l=>l.news||[]).concat(d.news_sources||[]);
const asksNews=/خبر|اخبار|انتقال|صفقه|صحافه/.test(nq);
if(/مباشر|الان|جاريه|حيه/.test(nq)){const live=matches.filter(m=>m.status==='in');return live.length?'المباريات المباشرة حالياً:\n'+live.slice(0,8).map(m=>teamAr(m.home?.name)+' '+(m.home?.score??'—')+' - '+(m.away?.score??'—')+' '+teamAr(m.away?.name)+'\n'+m.league+' · '+(m.detail||'مباشر')).join('\n\n'):'لا توجد مباراة مباشرة مؤكدة في البيانات الحالية.'}
if(/مباريات|جدول|اليوم|غدا|بكره|امس|مواعيد/.test(nq)){let wanted='today';if(/غدا|بكره/.test(nq))wanted='tomorrow';else if(/امس/.test(nq))wanted='yesterday';const now=new Date();const target=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Muscat',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(now.getTime()+(wanted==='tomorrow'?86400000:wanted==='yesterday'?-86400000:0)));const day=matches.filter(m=>{const dt=Date.parse(m.date||m.time||'');return Number.isFinite(dt)&&new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Muscat',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(dt))===target});return day.length?'مباريات '+(wanted==='today'?'اليوم':wanted==='tomorrow'?'غداً':'الأمس')+' بتوقيت عُمان:\n'+day.slice(0,12).map(m=>teamAr(m.home?.name)+' × '+teamAr(m.away?.name)+'\n'+formatDate(m.date||m.time)+' · '+m.league+' · '+(m.status==='post'?'انتهت':m.status==='in'?'مباشر':'لم تبدأ')).join('\n\n'):'لا توجد مباريات مدرجة لهذا اليوم في آخر تحديث.'}
if(asksNews){const soccerNewsPattern=/(كرة القدم|الدوري|دوري|كأس|كاس|نادي|الهلال|النصر|الاتحاد|الأهلي|الاهلي|ريال مدريد|برشلونة|ليفربول|مانشستر|رونالدو|ميسي|صلاح|انتقال|صفقة|مدرب|لاعب|football|soccer|champions league|premier league|transfer)/i;const recent=news.filter(n=>{const t=Date.parse(n.published||'');return n.headline&&n.source&&n.link&&/^https:\/\//.test(n.link)&&(/^(BBC Sport|Sky Sports|The Guardian|ESPN)$/i.test(n.source)||soccerNewsPattern.test((n.headline||'')+' '+(n.description||'')))&&Number.isFinite(t)&&Date.now()-t>=0&&Date.now()-t<=7*86400000}).sort((a,b)=>Date.parse(b.published||b.fetched_at)-Date.parse(a.published||a.fetched_at)).slice(0,6);return recent.length?'أحدث الأخبار المتاحة في الموقع:\n'+recent.map(n=>'• '+n.headline+' ('+(n.source||'مصدر رياضي')+')').join('\n'):'لا توجد أخبار مؤكدة متاحة حالياً.'}
const found=matches.filter(m=>{const names=normalize([m.home?.name,teamAr(m.home?.name),m.away?.name,teamAr(m.away?.name),m.league].join(' '));return names.split(/\s+/).some(w=>w.length>2&&nq.includes(w))||nq.includes(names)}).slice(0,5);
if(found.length)return found.map(m=>teamAr(m.home?.name)+' '+(m.status==='pre'?'—':m.home?.score??'0')+' - '+(m.status==='pre'?'—':m.away?.score??'0')+' '+teamAr(m.away?.name)+'\n'+m.league+' · '+formatDate(m.date||m.time)+' · '+(m.status==='post'?'انتهت':m.status==='in'?'مباشر':'لم تبدأ')).join('\n\n');
if(/ترتيب|الصداره|النقاط|جدول الدوري/.test(nq)){
const entries=Object.entries(d.leagues).filter(([,l])=>Array.isArray(l.standings)&&l.standings.length);
const words=nq.split(/\s+/).filter(w=>w.length>2);
const selected=entries.find(([key,l])=>{const name=normalize((l.name||'')+' '+key);return words.some(w=>name.includes(w))});
const chosen=selected?[selected]:entries.slice(0,5);
if(chosen.length)return 'جدول الترتيب حسب آخر بيانات الموقع:\n'+chosen.map(([key,l])=>(l.name||key)+'\n'+l.standings.slice(0,10).map((s,i)=>(s.rank||s.position||i+1)+'. '+teamAr(s.name||s.team?.name)+' — '+(s.points??'؟')+' نقطة').join('\n')).join('\n\n');
return 'جدول الترتيب غير متاح في البيانات الحالية.';
}
const leagues=[...new Set(Object.values(d.leagues).filter(l=>l.category==='football').map(l=>l.name).filter(Boolean))];
if(/دوري|بطوله|دوريات/.test(nq))return 'البطولات المتاحة في بيانات الموقع:\n'+leagues.slice(0,18).join('، ')+'\n\nاسألني عن اسم فريق أو مباراة محددة.';
return 'أستطيع مساعدتك في المباريات والنتائج المباشرة ومواعيد اليوم وغداً والأخبار والبطولات الموجودة في SLOOM365. اكتب اسم الفريق أو سؤالك بشكل أوضح، وسأجيب فقط بما تؤكده البيانات المتاحة.'}
launch.addEventListener('click',()=>{panel.classList.toggle('open');if(panel.classList.contains('open'))input.focus()});close.addEventListener('click',()=>panel.classList.remove('open'));
form.addEventListener('submit',async e=>{
e.preventDefault();
const q=input.value.trim();
if(!q||q.length>300)return;
if(turnstileSiteKey&&!turnstileToken){add('أكمل اختبار الحماية الظاهر أسفل المحادثة قبل الإرسال.','bot');return;}
const now=Date.now();
requests=requests.filter(t=>now-t<30000);
if(requests.length>=8){add('لحماية الخدمة المجانية، انتظر 30 ثانية قبل إرسال سؤال آخر.','bot');return}
requests.push(now);
input.value='';
add(q,'user');
send.disabled=true;send.textContent='…';
try{
const d=await getData();
let replied=false;
try{
const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,context:remoteContext(d),turnstileToken:turnstileToken||undefined})});
const payload=await response.json().catch(()=>({}));
if(response.ok&&typeof payload.answer==='string'&&payload.answer.trim()){
add(payload.answer.trim(),'bot');replied=true;
}
}catch(_){}
if(!replied){
const local=answer(q,d);
add(local+(local.startsWith('لا أستطيع تأكيد')?'':'\n\nملاحظة: هذه إجابة فورية من بيانات الموقع؛ خدمة الذكاء الاصطناعي المتقدمة لم تُفعّل بعد.'),'bot');
}
}catch(err){add('تعذر الوصول إلى بيانات الموقع الآن. حاول مرة أخرى بعد قليل.','bot')}
finally{if(turnstileWidget!==null&&window.turnstile){window.turnstile.reset(turnstileWidget);turnstileToken='';}send.disabled=false;send.textContent='إرسال';input.focus()}
});
async function setupTurnstile(){
 try{
  const r=await fetch('/api/chat',{method:'GET',cache:'no-store'});
  if(!r.ok)return;
  const p=await r.json();
  if(!p.turnstileSiteKey)return;
  turnstileSiteKey=p.turnstileSiteKey;
  const script=document.createElement('script');
  script.src='https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
  script.async=true;script.defer=true;
  script.onload=()=>{
   if(!window.turnstile)return;
   turnstileWidget=window.turnstile.render(captchaBox,{
    sitekey:turnstileSiteKey,
    callback:token=>{turnstileToken=token;},
    'expired-callback':()=>{turnstileToken='';},
    'error-callback':()=>{turnstileToken='';}
   });
  };
  document.head.appendChild(script);
 }catch(_){}
}
setupTurnstile();
add('مرحباً بك! أنا مساعد SLOOM365 المجاني. اسألني عن مباريات اليوم وغداً، النتائج، المباريات المباشرة، الأخبار أو ترتيب الدوريات. أعتمد على بيانات الموقع ولا أخمّن عند غياب المعلومة.','bot');
})();