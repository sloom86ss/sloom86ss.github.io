// Nabra Arabic TTS: mobile-friendly loader with CDN and WASM fallbacks.
const status = document.createElement('p');
status.className = 'note';
status.id = 'nabraStatus';
status.textContent = 'الصوت العربي الطبيعي مجاني ويُحمَّل عند الطلب. يحتاج اتصالاً مستقراً بالإنترنت ومساحة تخزين كافية.';
const toolRows = document.querySelectorAll('.tools');
const toolsRow = toolRows.length > 1 ? toolRows[1] : toolRows[0];
const button = document.createElement('button');
button.type = 'button';
button.className = 'btn gold';
button.id = 'nabraLoad';
button.textContent = '🎙️ تحميل الصوت العربي الطبيعي';
if (toolsRow) {
  toolsRow.appendChild(button);
  toolsRow.insertAdjacentElement('afterend', status);
}

let engine = null;
let loading = false;
let NabraTTSClass = null;

async function getNabraTTS() {
  if (NabraTTSClass) return NabraTTSClass;
  const sources = [
    'https://cdn.jsdelivr.net/npm/nabra-tts@0/+esm',
    'https://esm.sh/nabra-tts@latest?bundle'
  ];
  let lastError;
  for (const source of sources) {
    try {
      status.textContent = 'جارٍ فتح مكتبة الصوت...';
      const module = await import(source);
      if (module && module.NabraTTS) {
        NabraTTSClass = module.NabraTTS;
        return NabraTTSClass;
      }
      throw new Error('لم يتم العثور على محرك الصوت داخل المكتبة');
    } catch (error) {
      lastError = error;
      console.warn('Nabra CDN failed:', source, error);
    }
  }
  throw lastError || new Error('تعذر الوصول إلى مكتبة الصوت');
}

button.addEventListener('click', async () => {
  if (loading) return;
  if (engine) {
    status.textContent = 'الصوت العربي الطبيعي جاهز. اضغط «اقرأ آخر شرح» للتجربة.';
    return;
  }
  loading = true;
  button.disabled = true;
  button.textContent = '⏳ جارٍ تحميل الصوت...';
  status.textContent = 'جارٍ الاتصال بمصدر الصوت. أبقِ الصفحة مفتوحة ولا تغلق المتصفح.';
  try {
    const NabraTTS = await getNabraTTS();
    const progress = ({ file, loaded, total } = {}) => {
      const pct = total ? Math.min(100, Math.round(loaded / total * 100)) : null;
      status.textContent = (pct === null ? 'جارٍ تحميل ملفات الصوت' : 'تحميل الصوت: ' + pct + '%') +
        (file ? ' — ' + file : '') + '؛ لا تغلق الصفحة.';
    };

    try {
      engine = await NabraTTS.load({
        dtype: 'fp16', device: 'auto', cache: true, onProgress: progress
      });
    } catch (firstError) {
      console.warn('Nabra auto backend failed; retrying fp16 on WASM.', firstError);
      status.textContent = 'نجرب وضع التوافق مع الهاتف دون زيادة حجم النموذج...';
      engine = await NabraTTS.load({
        dtype: 'fp16', device: 'wasm', cache: true, onProgress: progress
      });
    }

    window.SmartEduNabraSpeak = async (text) => {
      try {
        await engine.speak(String(text));
        return true;
      } catch (error) {
        console.error('Nabra speech error:', error);
        return false;
      }
    };
    button.textContent = '✓ الصوت الطبيعي جاهز';
    status.textContent = 'تم تجهيز الصوت العربي الطبيعي وحفظ ملفاته في ذاكرة المتصفح. اضغط «اقرأ آخر شرح».';
  } catch (error) {
    console.error('Nabra load error:', error);
    const detail = String(error && (error.message || error.name) || error).slice(0, 180);
    status.textContent = 'فشل التحميل: ' + detail + '. جرّب اتصال Wi‑Fi ثم اضغط إعادة المحاولة.';
    button.textContent = '↻ إعادة محاولة تحميل الصوت';
  } finally {
    loading = false;
    button.disabled = false;
  }
});
