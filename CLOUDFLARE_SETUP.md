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
- وظيفة الشات تقبل POST من نفس النطاق فقط، وترفض الطلبات الكبيرة، وتتحقق من بنية البيانات وعمرها، ولا تكشف مفتاح Gemini للمتصفح.
- فعّل في لوحة Cloudflare قاعدة WAF / Rate limiting على المسار `/api/chat` للحد من الإغراق. في الخطة المجانية اختر Path = /api/chat، وحدّ 10 طلبات خلال 10 ثوانٍ لكل IP، والإجراء Block. الخطة المجانية تسمح بقاعدة Rate limiting واحدة وفترة 10 ثوانٍ.
- فعّل Bot Fight Mode إن كان متاحاً ضمن الخطة المجانية.
- لا تضع أسراراً أو مفاتيح API في ملفات HTML أو JavaScript العامة.

## مهم
- GitHub Pages لا يشغّل وظائف Cloudflare. سيبقى رابط GitHub Pages القديم كما هو إلى أن تنشر نسخة Cloudflare وتختبرها. لا تغيّر DNS أو تحذف الاستضافة القديمة قبل التأكد من عمل النسخة الجديدة.
- Cloudflare Pages له خطة مجانية بحدود استخدام؛ وGemini له حصة مجانية/حدود قد تتغير حسب الحساب والمنطقة. لذلك لا يمكن ضمان ذكاء اصطناعي غير محدود أو مجاني إلى الأبد.
