export async function onRequestPost({ request, env }) {
  const json = (data, status = 200) => new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store"
    }
  });

  const key = env.GEMINI_API_KEY;
  if (!key) return json({ error: "أضف GEMINI_API_KEY في إعدادات Cloudflare Pages." }, 503);

  let body;
  try {
    body = await request.json();
  } catch {
    return json({ error: "صيغة الطلب غير صحيحة." }, 400);
  }

  const question = typeof body?.question === "string" ? body.question.trim() : "";
  const context = body?.context;
  if (!question || question.length > 1000) {
    return json({ error: "اكتب سؤالاً لا يتجاوز 1000 حرف." }, 400);
  }
  if (!context || typeof context !== "object") {
    return json({ error: "بيانات الرياضة غير متاحة." }, 400);
  }

  const model = env.GEMINI_MODEL || "gemini-2.5-flash-lite";
  const system = "أنت سلوم AI، مساعد رياضي عربي. أجب بالعربية بوضوح. مصدر الحقائق الوحيد هو JSON المرفق من بيانات SLOOM TV. لا تخترع نتائج أو مواعيد أو ترتيباً أو إصابات أو تشكيلات أو أخباراً أو إحصائيات. إذا لم تتوفر المعلومة فقل ذلك صراحة ولا تخمن. لا تخلط البطولات. ميّز التحليل عن الحقيقة. إذا كانت البيانات stale=true أو قديمة فنبه المستخدم. اذكر المصدر ESPN ووقت التحديث عندما يتوفران. لا تدّع البحث في الإنترنت.";

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);
  try {
    const response = await fetch(
      "https://generativelanguage.googleapis.com/v1beta/models/" +
        encodeURIComponent(model) + ":generateContent?key=" + encodeURIComponent(key),
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          system_instruction: { parts: [{ text: system }] },
          contents: [{
            role: "user",
            parts: [{
              text: "بيانات الرياضة بصيغة JSON:\n" +
                JSON.stringify(context) + "\n\nسؤال المستخدم: " + question
            }]
          }],
          generationConfig: { temperature: 0.25, maxOutputTokens: 900 }
        })
      }
    );

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        return json({ error: "مفتاح Gemini غير صالح أو الحساب غير مؤهل للحصة المجانية." }, 502);
      }
      if (response.status === 429) {
        return json({ error: "انتهت الحصة المجانية مؤقتاً. حاول لاحقاً." }, 429);
      }
      return json({ error: "Gemini غير متاح حالياً. تحقق من إعداد النموذج." }, 502);
    }

    const answer = (payload.candidates?.[0]?.content?.parts || [])
      .map(part => part.text || "").join("").trim();
    if (!answer) return json({ error: "لم يصل رد واضح من Gemini." }, 502);
    return json({ answer, model });
  } catch (error) {
    return json({
      error: error.name === "AbortError"
        ? "تأخر الرد. أعد المحاولة."
        : "تعذر الاتصال بخدمة الذكاء الاصطناعي."
    }, error.name === "AbortError" ? 504 : 502);
  } finally {
    clearTimeout(timer);
  }
}

export async function onRequest(context) {
  if (context.request.method !== "POST") {
    return new Response(JSON.stringify({ error: "استخدم POST." }), {
      status: 405,
      headers: { "Content-Type": "application/json; charset=utf-8", "Allow": "POST", "Cache-Control": "no-store" }
    });
  }
  return onRequestPost(context);
}
