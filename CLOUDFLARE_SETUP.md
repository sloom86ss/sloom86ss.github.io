# تشغيل SLOOM365 على Cloudflare Pages (الخطة المجانية)

هذا المستودع جاهز للنشر على Cloudflare Pages مع وظيفة الشات الموجودة في `functions/api/chat.js`.

## النشر
1. أنشئ حساباً مجانياً في Cloudflare.
2. افتح Workers & Pages ثم Create application ثم Pages ثم Connect to Git.
3. اختر المستودع `sloom86ss/sloom86ss.github.io` والفرع `main`.
4. اترك Build command فارغاً، واجعل Build output directory هو `.`، ثم احفظ وانشر.
5. بعد نجاح النشر افتح رابط `pages.dev` الذي يمنحك إياه Cloudflare واختبر الصفحة و `/api/chat`.

## تفعيل الشات الذكي
1. أنشئ مفتاح Gemini API من Google AI Studio، وتحقق من الحصة المجانية المتاحة لحسابك ومن شروط استخدامها.
2. من Cloudflare Pages افتح المشروع ثم Settings ثم Variables and Secrets.
3. أضف `GEMINI_API_KEY` كـ Secret، وليس كمتغير عام ولا داخل ملفات GitHub.
4. أضف `GEMINI_MODEL` كمتغير اختياري وقيمته الافتراضية `gemini-3.5-flash-lite`.
5. أعد نشر المشروع بعد إضافة السر.

## الحماية
1. أنشئ Widget مجانياً في Cloudflare Turnstile، وأضف اسم مضيف مشروعك مثل `اسم-مشروعك.pages.dev`.
2. أضف `TURNSTILE_SITE_KEY` كمتغير عادي في Pages، وأضف `TURNSTILE_SECRET_KEY` كـ Secret. لا تضع المفتاح السري في GitHub أو في المحادثة.
3. أعد النشر. سيظهر اختبار الحماية داخل الشات، ويتحقق الخادم من الرمز قبل استدعاء Gemini.
4. إذا ربطت نطاقاً خاصاً بك عبر Cloudflare DNS، يمكنك إضافة قاعدة WAF Rate limiting على `/api/chat`: 10 طلبات خلال 10 ثوانٍ لكل IP والإجراء Block. قاعدة WAF لا تنطبق على نطاق `pages.dev` المشترك.
5. فعّل Bot Fight Mode إن كان متاحاً ضمن الخطة المجانية.

## مهم
- GitHub Pages لا يشغّل وظائف Cloudflare. سيبقى رابط GitHub Pages القديم كما هو إلى أن تنشر نسخة Cloudflare وتختبرها. لا تغيّر DNS أو تحذف الاستضافة القديمة قبل التأكد من عمل النسخة الجديدة.
- Cloudflare Pages له خطة مجانية بحدود استخدام؛ وGemini له حصة مجانية/حدود قد تتغير حسب الحساب والمنطقة. لذلك لا يمكن ضمان ذكاء اصطناعي غير محدود أو مجاني إلى الأبد.
