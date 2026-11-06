// Boy / girl voice preference controls for SMART EDU 360.
// Uses only Arabic voices actually available in the learner's device.
(() => {
  const panel = document.querySelector('.smart-voice-panel');
  const select = panel && panel.querySelector('select');
  if (!panel || !select) return;

  const note = panel.querySelector('small');
  const key = 'smartEdu360VoiceGender';
  const voiceKey = 'smartEdu360VoiceURI';
  const savedGender = localStorage.getItem(key) || '';
  const buttons = document.createElement('div');
  buttons.className = 'smart-voice-gender';
  buttons.setAttribute('role', 'group');
  buttons.setAttribute('aria-label', 'اختيار صوت المعلم');
  buttons.innerHTML =
    '<button type="button" data-gender="male" aria-pressed="false">👦 صوت ولد</button>' +
    '<button type="button" data-gender="female" aria-pressed="false">👧 صوت فتاة</button>';
  const style = document.createElement('style');
  style.textContent =
    '.smart-voice-gender{display:flex;gap:8px;flex-wrap:wrap;width:100%}' +
    '.smart-voice-gender button{flex:1;min-width:120px;padding:10px;border:1px solid #d5b86b;border-radius:10px;background:#101020;color:#fff;font:700 14px system-ui;cursor:pointer}' +
    '.smart-voice-gender button[aria-pressed="true"]{background:#d5b86b;color:#20172d;outline:2px solid #fff5}' ;
  document.head.appendChild(style);
  panel.insertBefore(buttons, select);

  const maleNames = /male|man|boy|ahmed|mohammed|muhammad|omar|ali|abdullah|naif|nayef|tarek|youssef|yusuf|khalid|sultan|hamza|majed|طارق|أحمد|محمد|عمر|علي|عبدالله/i;
  const femaleNames = /female|woman|girl|hoda|heba|sara|salma|farida|noura|haifa|reem|aya|aysha|mona|laila|layla|fatima|maryam|هدى|هبة|سارة|سلمى|نورة|هيفاء|ريم|آية|منى|ليلى|فاطمة|مريم/i;

  function voices() {
    return window.speechSynthesis
      ? window.speechSynthesis.getVoices().filter(v => /^ar([_-]|$)/i.test(v.lang))
      : [];
  }
  function matchVoice(gender) {
    const list = voices();
    const pattern = gender === 'male' ? maleNames : femaleNames;
    return list.find(v => pattern.test(v.name + ' ' + v.voiceURI)) || null;
  }
  function setActive(gender) {
    buttons.querySelectorAll('button').forEach(b => {
      b.setAttribute('aria-pressed', String(b.dataset.gender === gender));
    });
  }
  function choose(gender) {
    localStorage.setItem(key, gender);
    setActive(gender);
    const voice = matchVoice(gender);
    if (!voice) {
      if (note) note.textContent = gender === 'male'
        ? 'لم أجد صوت ولد عربيًا محددًا في أصوات جهازك. اختر صوتًا عربيًا من القائمة أو ثبّت صوتًا مناسبًا في إعدادات الجهاز.'
        : 'لم أجد صوت فتاة عربيًا محددًا في أصوات جهازك. اختر صوتًا عربيًا من القائمة أو ثبّت صوتًا مناسبًا في إعدادات الجهاز.';
      return;
    }
    select.value = voice.voiceURI;
    localStorage.setItem(voiceKey, voice.voiceURI);
    if (note) note.textContent = 'تم اختيار الصوت المتاح: ' + voice.name + '. اضغط «تجربة الصوت» للاستماع.';
    window.speechSynthesis.cancel();
  }

  buttons.addEventListener('click', event => {
    const button = event.target.closest('button[data-gender]');
    if (button) choose(button.dataset.gender);
  });
  select.addEventListener('change', () => {
    localStorage.setItem(voiceKey, select.value);
    if (note) note.textContent = 'تم اختيار صوت الجهاز. قد لا يحدد المتصفح جنس الصوت بدقة؛ استمع إلى العينة للتأكد.';
  });
  if (savedGender) setActive(savedGender);
  window.speechSynthesis?.addEventListener('voiceschanged', () => {
    const gender = localStorage.getItem(key);
    if (gender && matchVoice(gender)) choose(gender);
  });
})();