const MAX_BODY_BYTES = 64 * 1024;
const MAX_AGE_MS = 90 * 60 * 1000;

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff"
    }
  });
}

function cleanText(value, max = 240) {
  return typeof value === "string" ? value.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").slice(0, max) : "";
}

function cleanNews(item) {
  if (!item || typeof item !== "object") return null;
  return {
    headline: cleanText(item.headline || item.title, 220),
    description: cleanText(item.description || item.summary, 420),
    published: cleanText(item.published || item.published_at, 50),
    source: cleanText(item.source || item.source_name, 100),
    link: cleanText(item.link || item.url, 500)
  };
}

function safeContext(input) {
  const generated = Date.parse(input.generated_at || "");
  const age = Date.now() - generated;
  const fresh = Number.isFinite(generated) && age >= 0 && age <= MAX_AGE_MS;
  const sourceNews = Array.isArray(input.news_sources) ? input.news_sources : [];
  const rawLeagues = Array.isArray(input.leagues)
    ? input.leagues
    : Object.values(input.leagues || {});
  const leagues = fresh ? rawLeagues.slice(0, 30).map((league) => {
    const matches = Array.isArray(league.matches) ? league.matches : [];
    const standings = Array.isArray(league.standings) ? league.standings : [];
    const news = Array.isArray(league.news) ? league.news : [];
    return {
      name: cleanText(league.name, 100),
      updated_at: cleanText(league.updated_at, 50),
      stale: Boolean(league.stale),
      matches: matches.slice(0, 40).map((m) => ({
        date: cleanText(m.date || m.time, 50),
        status: cleanText(m.status, 30),
        detail: cleanText(m.detail, 100),
        home: { name: cleanText(m.home?.name, 100), score: cleanText(String(m.home?.score ?? ""), 8) },
        away: { name: cleanText(m.away?.name, 100), score: cleanText(String(m.away?.score ?? ""), 8) }
      })),
      standings: standings.slice(0, 20).map((s) => ({
        name: cleanText(s.name || s.team?.name, 100),
        points: cleanText(String(s.points ?? ""), 8),
        position: cleanText(String(s.position ?? s.rank ?? ""), 8)
      })),
      news: news.slice(0, 10).map(cleanNews).filter(Boolean)
    };
  }).filter((l) => !l.stale) : [];
  return {
    provider: cleanText(input.provider, 80),
    generated_at: cleanText(input.generated_at, 50),
    timezone: "Asia/Muscat",
    dataset_fresh: fresh,
    news_sources: fresh ? sourceNews.slice(0, 20).map(cleanNews).filter(Boolean) : [],
    leagues
  };
}

export async function onRequestPost({ request, env }) {
  if (request.headers.get("Origin") !== new URL(request.url).origin) {
    return json({ error: "تم رفض الطلب لأسباب أمنية." }, 403);
  }
  const length = Number(request.headers.get("Content-Length") || 0);
  if (length > MAX_BODY_BYTES) return json({ error: "حجم الطلب أكبر من المسموح." }, 413);

  let body;
  try {
    const raw = await request.text();
    if (new TextEncoder().encode(raw).byteLength > MAX_BODY_BYTES) {
      return json({ error: "حجم الطلب أكبر من المسموح." }, 413);
    }
    body = JSON.parse(raw);
  } catch {
    return json({ error: "صيغة الطلب غير صحيحة." }, 400);
  }

  const question = cleanText(body?.question, 1000).trim();
  if (!question) return json({ error: "اكتب سؤالاً واضحاً لا يتجاوز 1000 حرف." }, 400);

  const context = safeContext(body?.context || {});
  if (!context.dataset_fresh) {
    return json({ error: "توقفت الإجابة الذكية لأن آخر تحديث للبيانات تجاوز 90 دقيقة. لا نعرض معلومات قديمة على أنها مباشرة." }, 409);
  }

  if (env.TURNSTILE_SECRET_KEY) {
    const token = cleanText(body?.turnstileToken, 2048);
    if (!token) return json({ error: "أكمل اختبار الحماية قبل الإرسال." }, 403);
    const verification = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        secret: env.TURNSTILE_SECRET_KEY,
        response: token,
        remoteip: request.headers.get("CF-Connecting-IP") || ""
      })
    }).catch(() => null);
    if (!verification) return json({ error: "تعذر التحقق من اختبار الحماية." }, 502);
    const result = await verification.json().catch(() => ({}));
    if (!result.success) return json({ error: "فشل اختبار الحماية. أعد المحاولة." }, 403);
  }

  if (env.TURNSTILE_SECRET_KEY) {
    const token = cleanText(body?.turnstileToken, 2048);
    if (!token) return json({ error: "أكمل اختبار الحماية قبل الإرسال." }, 403);
    let verification;
    try {
      verification = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          secret: env.TURNSTILE_SECRET_KEY,
          response: token,
          remoteip: request.headers.get("CF-Connecting-IP") || ""
        })
      });
    } catch {
      return json({ error: "تعذر التحقق من اختبار الحماية." }, 502);
    }
    const result = await verification.json().catch(() => ({}));
    if (!result.success) return json({ error: "فشل اختبار الحماية. أعد المحاولة." }, 403);
  }

  const key = env.GEMINI_API_KEY;
  if (!key) return json({ error: "خدمة الذكاء الاصطناعي لم تُفعّل بعد. أضف المفتاح السري في إعدادات Cloudflare Pages." }, 503);

  const model = env.GEMINI_MODEL || "gemini-3.5-flash-lite";
  const system = "أنت مساعد SLOOM365 لكرة القدم فقط. أجب بالعربية الفصحى الواضحة. اعتمد حصراً على JSON المرفق. لا تخترع نتائج أو مواعيد أو إحصائيات أو تشكيلات أو إصابات أو قنوات. لا تعرض أي معلومة غير موجودة في البيانات. ميّز التحليل عن الحقائق، وميّز الشائعة عن الخبر المؤكد. إذا لم تتوفر المعلومة فقل إنها غير متاحة. لا تصف أي خبر بأنه حصري دون دليل صريح في المصدر.";
  const prompt = "بيانات كرة القدم المؤكدة زمنياً بصيغة JSON:\n" +
    JSON.stringify(context) + "\n\nسؤال المستخدم: " + question;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
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
          contents: [{ role: "user", parts: [{ text: prompt }] }],
          generationConfig: { temperature: 0.2, maxOutputTokens: 1000 }
        })
      }
    );
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 429) return json({ error: "انتهت الحصة المجانية مؤقتاً. حاول لاحقاً." }, 429);
      return json({ error: "خدمة الذكاء الاصطناعي غير متاحة حالياً." }, 502);
    }
    const answer = (payload.candidates?.[0]?.content?.parts || [])
      .map((part) => part.text || "").join("").trim();
    if (!answer) return json({ error: "لم يصل رد واضح من المساعد." }, 502);
    return json({ answer, model });
  } catch (error) {
    return json({
      error: error.name === "AbortError" ? "تأخر الرد. حاول مرة أخرى." : "تعذر الاتصال بخدمة الذكاء الاصطناعي."
    }, error.name === "AbortError" ? 504 : 502);
  } finally {
    clearTimeout(timer);
  }
}

export async function onRequest({ request, env }) {
  if (request.method === "GET") {
    return json({ turnstileSiteKey: cleanText(env.TURNSTILE_SITE_KEY, 200) });
  }
  return json({ error: "استخدم POST." }, 405);
}
