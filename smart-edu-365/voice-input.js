(()=> {
 const input=document.getElementById('question');
 const send=document.getElementById('send');
 const row=input?.parentElement;
 if(!input||!send||!row)return;
 const style=document.createElement('style');
 style.textContent='.voice-input-tools{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:center}.voice-input-tools button{border:1px solid #a98bff88;border-radius:12px;padding:10px 14px;background:#302653;color:#fff;font:700 14px system-ui;cursor:pointer}.voice-input-tools button:disabled{opacity:.5}.voice-input-status{font-size:12px;color:#d0c9e4;min-height:22px}';
 document.head.appendChild(style);
 const tools=document.createElement('div');tools.className='voice-input-tools';
 const mic=document.createElement('button');mic.type='button';mic.textContent='🎙️ تحدث إلى المعلّم';
 const stop=document.createElement('button');stop.type='button';stop.textContent='⏹ إيقاف الاستماع';stop.disabled=true;
 const status=document.createElement('span');status.className='voice-input-status';status.setAttribute('role','status');status.textContent='يمكنك الكتابة أو استخدام الميكروفون إذا كان متصفحك يدعمه.';
 tools.append(mic,stop,status);row.insertAdjacentElement('afterend',tools);
 const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
 let recognition=null,active=false;
 if(!Recognition){mic.disabled=true;status.textContent='الإملاء الصوتي غير مدعوم في هذا المتصفح. يمكنك الكتابة بدلاً منه.';}
 else {
  recognition=new Recognition();recognition.lang='ar-OM';recognition.continuous=false;recognition.interimResults=false;recognition.maxAlternatives=1;
  recognition.onstart=()=>{active=true;mic.disabled=true;stop.disabled=false;status.textContent='أستمع إليك الآن... تحدث بوضوح.';};
  recognition.onresult=e=>{const transcript=e.results?.[0]?.[0]?.transcript?.trim();if(transcript){input.value=transcript;status.textContent='سمعت: '+transcript;send.click();}else status.textContent='لم أتمكن من فهم الكلام. حاول مرة أخرى أو اكتب سؤالك.';};
  recognition.onerror=e=>{const messages={ 'not-allowed':'لم يُسمح باستخدام الميكروفون. فعّل إذن الميكروفون للموقع.','service-not-allowed':'خدمة التعرف على الصوت غير متاحة.','no-speech':'لم أسمع صوتاً. حاول مرة أخرى.','audio-capture':'لم يتم العثور على ميكروفون.'};status.textContent=messages[e.error]||'حدثت مشكلة في الاستماع: '+e.error;};
  recognition.onend=()=>{active=false;mic.disabled=false;stop.disabled=true;};
  mic.addEventListener('click',()=>{try{recognition.start();}catch(e){status.textContent='الاستماع جارٍ بالفعل أو تعذر تشغيله. حاول مجدداً.';}});
  stop.addEventListener('click',()=>{if(active)recognition.stop();});
 }
 const chat=document.getElementById('chat');
 if(chat){
  const observer=new MutationObserver(records=>{
   for(const record of records)for(const node of record.addedNodes){
    if(node.nodeType!==1||!node.classList.contains('bubble')||!node.classList.contains('teacher'))continue;
    const text=node.innerText.replace(/^المعلّم\s*/,'').trim();
    if(text&&window.SmartEduVoice)window.SmartEduVoice.speak(text,.86);
   }
  });
  observer.observe(chat,{childList:true});
 }
})();