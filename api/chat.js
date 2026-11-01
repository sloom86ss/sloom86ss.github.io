export default async function handler(req,res){
 res.setHeader("Cache-Control","no-store");
 if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).json({error:"استخدم POST."});}
 const body=req.body||{};
 const mode=body.mode==="translate"?"translate":"chat";
 const key=process.env.GEMINI_API_KEY;
 if(mode==="translate"){
  const items=Array.isArray(body.items)?body.items.slice(0,18):[];
  if(!items.length)return res.status(400).json({error:"لا توجد أخبار لترجمتها."});
  if(!key)return res.status(503).json({error:"ترجمة الأخبار تحتاج إعداد GEMINI_API_KEY في إعدادات الاستضافة."});
  const prompt="ترجم عناوين الأخبار وأوصافها إلى العربية الفصحى بأسلوب صحفي رياضي طبيعي. لا تضف حقائق أو تفاصيل. أعد JSON صالحاً فقط بالشكل {\"translations\":[{\"headline\":\"...\",\"description\":\"...\"}]} وبنفس ترتيب وعدد العناصر. البيانات: "+JSON.stringify(items);
  return callGemini(req,res,key,prompt,true);
 }
 const question=typeof body.question==="string"?body.question.trim():"";
 const context=body.context;
 if(!question||question.length>1000)return res.status(400).json({error:"اكتب سؤالاً لا يتجاوز 1000 حرف."});
 if(!context||typeof context!=="object")return res.status(400).json({error:"بيانات الرياضة غير متاحة."});
 if(!key)return res.status(200).json({answer:localAnswer(question,context),mode:"local",notice:"المساعد يعمل بالبيانات الحالية، لكن التحليل التوليدي يحتاج إعداد مفتاح Gemini سري على الاستضافة."});
 const system="أنت SLOOM360، محلل رياضي ومراسل عربي محترف. أجب بالعربية الفصحى حصراً، حتى لو كانت أسماء الفرق والأخبار في المصدر بالإنجليزية. استخدم أسماء الأندية العربية المعروفة، ويمكن وضع الاسم الأصلي بين قوسين عند الحاجة. اعتمد فقط على JSON المرفق. حلل النتائج والأداء والاتجاهات الحسابية المتاحة، ولخص الأخبار والمباريات مع ذكر المصدر. افصل بين الحقائق والتحليل. لا تخترع أحداثاً أو إحصائيات أو تشكيلات أو إصابات أو مواعيد. إذا لم تتوفر معلومة فقل ذلك صراحة. انتبه إلى stale=true ووقت التحديث والمنطقة الزمنية Asia/Muscat. لا تدّع أنك بحثت خارج البيانات.";
 const prompt="بيانات الرياضة بصيغة JSON:\n"+JSON.stringify(context)+"\n\nسؤال المستخدم: "+question;
 return callGemini(req,res,key,prompt,false,system);
}
function localAnswer(q,c){
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
