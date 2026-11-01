export default async function handler(req,res){
 res.setHeader("Cache-Control","no-store");
 if(req.method!=="POST"){res.setHeader("Allow","POST");return res.status(405).json({error:"استخدم POST."});}
 const key=process.env.GEMINI_API_KEY;
 if(!key)return res.status(503).json({error:"أضف مفتاح Gemini في إعدادات Vercel أولاً."});
 const question=typeof req.body?.question==="string"?req.body.question.trim():"";
 const context=req.body?.context;
 if(!question||question.length>1000)return res.status(400).json({error:"اكتب سؤالاً لا يتجاوز 1000 حرف."});
 if(!context||typeof context!=="object")return res.status(400).json({error:"بيانات الرياضة غير متاحة."});
 const model=process.env.GEMINI_MODEL||"gemini-2.5-flash-lite";
 const system="أنت سلوم AI، مساعد رياضي عربي. أجب بالعربية بوضوح. مصدر الحقائق الوحيد هو JSON المرفق من بيانات SLOOM TV. لا تخترع نتائج أو مواعيد أو ترتيباً أو إصابات أو تشكيلات أو أخباراً أو إحصائيات. إذا لم تتوفر المعلومة فقل ذلك صراحة ولا تخمن. لا تخلط البطولات. ميّز التحليل عن الحقيقة. إذا كانت البيانات stale=true أو قديمة فنبه المستخدم. اذكر المصدر ESPN ووقت التحديث عندما يتوفران. لا تدّع البحث في الإنترنت.";
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),25000);
 try{
  const r=await fetch("https://generativelanguage.googleapis.com/v1beta/models/"+encodeURIComponent(model)+":generateContent?key="+encodeURIComponent(key),{method:"POST",headers:{"Content-Type":"application/json"},signal:controller.signal,body:JSON.stringify({system_instruction:{parts:[{text:system}]},contents:[{role:"user",parts:[{text:"بيانات الرياضة بصيغة JSON:\n"+JSON.stringify(context)+"\n\nسؤال المستخدم: "+question}]}],generationConfig:{temperature:0.25,maxOutputTokens:900}})});
  const p=await r.json().catch(()=>({}));
  if(!r.ok){if(r.status===401||r.status===403)return res.status(502).json({error:"مفتاح Gemini غير صالح أو الحساب غير مؤهل للحصة المجانية."});if(r.status===429)return res.status(429).json({error:"انتهت الحصة المجانية مؤقتاً. حاول لاحقاً."});return res.status(502).json({error:"Gemini غير متاح حالياً. تحقق من إعداد النموذج."});}
  const answer=(p.candidates?.[0]?.content?.parts||[]).map(x=>x.text||"").join("").trim();
  if(!answer)return res.status(502).json({error:"لم يصل رد واضح من Gemini."});
  return res.status(200).json({answer,model});
 }catch(e){return res.status(e.name==="AbortError"?504:502).json({error:e.name==="AbortError"?"تأخر الرد. أعد المحاولة.":"تعذر الاتصال بخدمة الذكاء الاصطناعي."});}
 finally{clearTimeout(timer);}
}