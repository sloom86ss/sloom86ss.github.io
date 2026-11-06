(()=> {
 const KEY='smartEdu360VoiceURI';
 const synth=window.speechSynthesis;
 if(!synth)return;
 const style=document.createElement('style');
 style.textContent=`
 .smart-voice-panel{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:12px 0 18px;padding:12px 14px;border:1px solid #a98bff77;border-radius:15px;background:linear-gradient(135deg,#211d3b,#151528);color:#fff;font:14px/1.6 system-ui,Tahoma,sans-serif}
 .smart-voice-panel label{font-weight:800;color:#ffe09a}
 .smart-voice-panel select{flex:1;min-width:160px;max-width:100%;padding:10px;border:1px solid #8f7ac4;border-radius:10px;background:#101020;color:#fff;font:inherit}
 .smart-voice-panel button{padding:9px 13px;border:1px solid #d5b86b;border-radius:10px;background:#d5b86b;color:#20172d;font:700 13px system-ui;cursor:pointer}
 .smart-voice-panel small{flex-basis:100%;color:#d0c9e4;font-size:11px}
 `;
 document.head.appendChild(style);
 const panel=document.createElement('section');
 panel.className='smart-voice-panel';
 panel.setAttribute('aria-label','إعدادات صوت المتحدث');
 panel.innerHTML='<label for="smartVoiceSelect">🎙️ اختر صوت المتحدث</label><select id="smartVoiceSelect" aria-label="اختر صوت المتحدث"><option>جارٍ تحميل الأصوات العربية...</option></select><button type="button" id="smartVoiceTest">▶ تجربة الصوت</button><small id="smartVoiceNote">اختر الصوت الذي تفضله؛ سيُحفظ اختيارك للاختبارات والمعلم الذكي على هذا الجهاز.</small>';
 const main=document.querySelector('main')||document.body;
 const anchor=main.querySelector('header')||main.firstElementChild;
 if(anchor&&anchor.parentNode===main)anchor.insertAdjacentElement('afterend',panel);else main.prepend(panel);
 const select=panel.querySelector('select'),note=panel.querySelector('small');
 let voices=[];
 function load(){
   voices=synth.getVoices().filter(v=>/^ar([_-]|$)/i.test(v.lang));
   const saved=localStorage.getItem(KEY);
   select.innerHTML='';
   if(!voices.length){
     const opt=document.createElement('option');opt.value='';opt.textContent='لا توجد أصوات عربية مثبتة';select.appendChild(opt);select.disabled=true;
     note.textContent='ثبّت صوتاً عربياً من إعدادات تحويل النص إلى كلام في جهازك، ثم أعد فتح الموقع.';
     return;
   }
   select.disabled=false;
   voices.forEach(v=>{const o=document.createElement('option');o.value=v.voiceURI;o.textContent=v.name+' — '+v.lang;select.appendChild(o)});
   const chosen=voices.find(v=>v.voiceURI===saved)||voices[0];
   select.value=chosen.voiceURI;
   if(!saved)localStorage.setItem(KEY,chosen.voiceURI);
   note.textContent='الصوت المختار: '+chosen.name+'. اضغط «تجربة الصوت» لسماع عينة.';
 }
 function selected(){return voices.find(v=>v.voiceURI===select.value)||voices[0]||null}
 function speak(text,rate=.88){
   if(!text)return false;
   if(!voices.length)return false;
   synth.cancel();
   const u=new SpeechSynthesisUtterance(String(text));
   const v=selected();if(v){u.voice=v;u.lang=v.lang}
   u.rate=rate;synth.speak(u);return true;
 }
 select.addEventListener('change',()=>{localStorage.setItem(KEY,select.value);synth.cancel();const v=selected();note.textContent=v?'تم اختيار: '+v.name:'اختر صوتاً عربياً';});
 panel.querySelector('#smartVoiceTest').addEventListener('click',()=>speak('مرحباً! هذا هو الصوت الذي اخترته. أتمنى لك تعلماً ممتعاً وناجحاً.',.88));
 synth.addEventListener?.('voiceschanged',load);
 load();
 window.SmartEduVoice={speak,selectedVoice:selected,refresh:load};
})();