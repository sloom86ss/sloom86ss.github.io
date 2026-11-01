export default async function handler(req,res){
 res.setHeader("Cache-Control","no-store");
 if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).json({error:"استخدم POST."});}
 const body=req.body||{};
 const mode=body.mode==="translate"?"translate":"chat";
 const key=process.env.GEMINI_API_KEY;
 if(mode==="translate"){
  const items=Array.isArray(body.items)?body.items.slice(0,100):[];
  if(!items.length)return res.status(400).json({error:"لا توجد أخبار لترجمتها."});
  if(!key)return res.status(503).json({error:"ترجمة الأخبار تحتاج إعداد GEMINI_API_KEY في إعدادات الاستضافة."});
  const prompt="حوّل كل خبر إلى بطاقة عربية فصحى. ترجم العنوان والوصف، واكتب ملخصاً تحريرياً موجزاً من جملة أو جملتين مستنداً حصراً إلى النص المقدم، دون إضافة وقائع. صنّف الخبر transfers إذا كان عن انتقال أو مفاوضات أو إعارة أو تجديد عقد، وإلا news. أعد JSON فقط بالشكل {\"translations\":[{\"headline\":\"...\",\"description\":\"...\",\"summary\":\"...\",\"category\":\"news|transfers\"}]} وبنفس ترتيب وعدد العناصر. إذا كان العنصر مجرد اسم نادٍ فترجم الاسم في headline واترك بقية الحقول فارغة. البيانات: "+JSON.stringify(items);
  return callGemini(req,res,key,prompt,true);
 }
 const question=typeof body.question==="string"?body.question.trim():"";
 const context=body.context;
 if(!question||question.length>1000)return res.status(400).json({error:"اكتب سؤالاً لا يتجاوز 1000 حرف."});
 if(!context||typeof context!=="object")return res.status(400).json({error:"بيانات الرياضة غير متاحة."});
 const now=Date.now();
 const generated=Date.parse(context.generated_at||"");
 const datasetFresh=Number.isFinite(generated)&&now-generated>=0&&now-generated<=90*60*1000;
 const isRecent=(value,hours)=>{const t=Date.parse(value||'');return Number.isFinite(t)&&now-t>=0&&now-t<=hours*60*60*1000;};
 const allLeagues=Array.isArray(context.leagues)?context.leagues:Object.values(context.leagues||{});
 const safeContext={provider:context.provider,generated_at:context.generated_at,timezone:'Asia/Muscat',dataset_fresh:datasetFresh,
  news_sources:datasetFresh?(context.news_sources||[]).filter(n=>isRecent(n.published,7)):[],
  leagues:datasetFresh?allLeagues.filter(l=>!l.stale&&isRecent(l.updated_at,1.5)).map(l=>({...l,news:(l.news||[]).filter(n=>isRecent(n.published,7))})):[]};
 if(!key)return res.status(200).json({answer:localAnswer(question,safeContext),mode:"local",notice:datasetFresh?"المعلومات حديثة وفق آخر تحديث مؤكد. التحليل التوليدي يحتاج إعداد مفتاح Gemini.":"توقف البوت لأن آخر تحديث تجاوز 90 دقيقة؛ لا نعرض بيانات قديمة على أنها مباشرة."});
 const prompt="بيانات الرياضة المفلترة زمنياً بصيغة JSON:\n"+JSON.stringify(safeContext)+"\n\nسؤال المستخدم: "+question;
 return callGemini(req,res,key,prompt,false,system);
 const system="أنت SLOOM360، مساعد متخصص بكرة القدم العالمية فقط، ومحلل رياضي ومراسل عربي محترف. أجب بالعربية الفصحى حصراً، حتى لو كانت أسماء الفرق والأخبار في المصدر بالإنجليزية. استخدم أسماء الأندية العربية المعروفة، ويمكن وضع الاسم الأصلي بين قوسين عند الحاجة. اعتمد فقط على JSON المرفق. إذا كانت dataset_fresh=false فلا تعرض أي نتائج أو أخبار أو حالة مباشرة. حلل النتائج والأداء والاتجاهات الحسابية المتاحة، ولخص الأخبار والمباريات مع ذكر المصدر. افصل بين الحقائق والتحليل. لا تخترع أحداثاً أو إحصائيات أو تشكيلات أو إصابات أو مواعيد. إذا كانت dataset_fresh=false فلا تعرض نتائج أو أخباراً أو حالة مباشرة. لا تعرض خبراً يتجاوز سبعة أيام أو بلا تاريخ نشر، ولا تستخدم دورياً موسوماً stale=true. إذا لم تتوفر معلومة فقل ذلك صراحة. انتبه إلى stale=true ووقت التحديث والمنطقة الزمنية Asia/Muscat. لا تدّع أنك بحثت خارج البيانات. عند السؤال عن انتقالات أو خبر عاجل، اذكر وقت النشر والمصدر والرابط إن توفرت، وميّز الشائعة عن التأكيد الرسمي. لا تصف خبراً بأنه حصري إلا إذا نص المصدر على ذلك.";
 const prompt="بيانات الرياضة المفلترة زمنياً والمتحقق من حداثتها بصيغة JSON:\n"+JSON.stringify(safeContext)+"\n\nسؤال المستخدم: "+question;
 return callGemini(req,res,key,prompt,false,system);
}
function localAnswer(q,c){
 if(!c.dataset_fresh)return 'توقفت عن عرض النتائج والأخبار لأن آخر تحديث مؤكد تجاوز 90 دقيقة. لا أستطيع تأكيد الحالة الحالية الآن؛ حاول بعد نجاح التحديث القادم.';
 const s=q.toLowerCase(), leagues=Object.values(c.leagues||{}), matches=leagues.flatMap(l=>(l.matches||[]).map(m=>({...m,league:l.name||"بطولة"}))), news=[...(c.news_sources||[]),...leagues.flatMap(l=>l.news||[])];
 const arabicNames={"Manchester City":"مانشستر سيتي","Manchester United":"مانشستر يونايتد","Liverpool":"ليفربول","Arsenal":"أرسنال","Chelsea":"تشيلسي","Real Madrid":"ريال مدريد","Barcelona":"برشلونة","Bayern Munich":"بايرن ميونخ","Al Hilal":"الهلال","Al Nassr":"النصر","Al-Ittihad":"الاتحاد","Al Ahli":"الأهلي"};
 const team=n=>arabicNames[n]||n||"الفريق";
 if(/خبر|أخبار|ملخص|لخص|آخر/.test(s)){
  if(!news.length)return "لا توجد أخبار متاحة في البيانات الحالية. تحقق من تحديث المصادر لاحقاً.";
  return "إليك أحدث الأخبار المتاحة من المصادر:\n"+news.slice(0,8).map((n,i)=>(i+1)+". "+(n.headline||"خبر رياضي")+" — "+(n.source||"المصدر")+(n.link?"\n"+n.link:"")).join("\n\n")+"\n\nملاحظة: هذا عرض للبيانات المتاحة، والترجمة والتحليل المتقدم يحتاجان تفعيل خدمة الذكاء الاصطناعي.";
 }
 if(/مبار|نتائج|مواعيد|اليوم|أمس|غد/.test(s)){
  if(!matches.length)return "لا توجد مباريات مسجلة حالياً. قد يكون مصدر النتائج لم يحدّث بياناته بعد.";
  return "المباريات المتوفرة في قاعدة البيانات:\n"+matches.slice(0,15).map(m=>team(m.home?.name)+" "+(m.home?.score??"—")+" - "+(m.away?.score??"—")+" "+team(m.away?.name)+" · "+m.league+" · "+(m.date||"موعد غير محدد")).join("\n");
 }
 const standings=leagues.flatMap(l=>(l.standings||[]).slice(0,3).map(x=>l.name+": "+team(x.name)+" — "+x.points+" نقطة"));
 if(/ترتيب|جدول|متصدر/.test(s)&&standings.length)return "أبرز بيانات الترتيب المتاحة:\n"+standings.slice(0,12).join("\n");
 return "أنا مساعد SLOOM360. أستطيع عرض الأخبار والمباريات والترتيب الموجودة في قاعدة البيانات. جرّب أن تسأل: ما نتائج اليوم؟ أو لخّص آخر الأخبار.\n\nالمساعد الأساسي يعمل، لكن التحليل الذكي والترجمة التلقائية يحتاجان إعداد GEMINI_API_KEY في إعدادات الاستضافة.";
}
async function callGemini(req,res,key,prompt,isJson,system){
 const model=process.env.GEMINI_MODEL||"gemini-2.5-flash-lite";
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);
 try{
  const r=await fetch("https://generativelanguage.googleapis.com/v1beta/models/"+encodeURIComponent(model)+":generateContent?key="+encodeURIComponent(key),{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,body:JSON.stringify({...(system?{system_instruction:{parts:[{text:system}]}}:{}),contents:[{role:"user",parts:[{text:prompt}]}],generationConfig:{temperature:isJson?0.1:0.25,maxOutputTokens:isJson?3500:1200,...(isJson?{responseMimeType:"application/json"}:{})}})});
  const p=await r.json().catch(()=>({}));
  if(!r.ok){if(r.status===401||r.status===403)return res.status(502).json({error:"مفتاح Gemini غير صالح أو الحساب غير مؤهل للحصة المجانية."});if(r.status===429)return res.status(429).json({error:"انتهت الحصة المجانية مؤقتاً. حاول لاحقاً."});return res.status(502).json({error:"خدمة الذكاء الاصطناعي غير متاحة حالياً."});}
  const answer=(p.candidates?.[0]?.content?.parts||[]).map(x=>x.text||"").join("").trim();
  if(!answer)return res.status(502).json({error:"لم يصل رد واضح من Gemini."});
  if(isJson){try{return res.status(200).json(JSON.parse(answer));}catch{return res.status(502).json({error:"تعذر قراءة الترجمة. أعد المحاولة."});}}
  return res.status(200).json({answer,model});
 }catch(e){return res.status(e.name==="AbortError"?504:502).json({error:e.name==="AbortError"?"تأخر الرد. أعد المحاولة.":"تعذر الاتصال بخدمة الذكاء الاصطناعي."});}
 finally{clearTimeout(timer);}
}
