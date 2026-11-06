// Selectable female Arabic neural voice with a reliable device-voice fallback.
(() => {
  const panel = document.querySelector('.smart-voice-panel');
  const select = panel && panel.querySelector('select');
  if (!select) return;

  const voiceKey = 'smartEdu360VoiceURI';
  const modeKey = 'smartEdu360VoiceMode';
  const note = panel.querySelector('small');
  let mode = localStorage.getItem(modeKey) || 'nabra-neural';

  function ensureNeuralOption() {
    if (!Array.from(select.options).some(o => o.value === 'nabra-neural')) {
      const option = document.createElement('option');
      option.value = 'nabra-neural';
      option.textContent = 'نبرة — صوت فتاة عربية فصحى';
      select.insertBefore(option, select.firstChild);
    }
    select.disabled = false;
  }

  function deviceVoices() {
    const synth = window.speechSynthesis;
    return synth ? synth.getVoices().filter(v => /^ar([_-]|$)/i.test(v.lang)) : [];
  }

  function updateNote(message) {
    if (!note) return;
    if (message) { note.textContent = message; return; }
    if (select.value === 'nabra-neural') {
      note.textContent = window.SmartEduNabraSpeak
        ? 'صوت الفتاة العربية الفصحى جاهز.'
        : 'صوت الفتاة الطبيعي لم يُحمّل بعد؛ سيعمل الصوت العربي المتاح في جهازك مؤقتاً.';
    } else {
      const v = deviceVoices().find(v => v.voiceURI === select.value);
      note.textContent = v ? 'تم اختيار صوت الجهاز: ' + v.name : 'سيُستخدم الصوت العربي المتاح في جهازك.';
    }
  }

  function restoreChoice() {
    ensureNeuralOption();
    if (mode === 'nabra-neural') {
      select.value = 'nabra-neural';
    } else {
      const savedVoice = localStorage.getItem(voiceKey);
      if (savedVoice && Array.from(select.options).some(o => o.value === savedVoice)) {
        select.value = savedVoice;
      } else {
        select.value = 'nabra-neural';
        mode = 'nabra-neural';
      }
    }
    updateNote();
  }

  function speakWithDevice(text, rate) {
    const synth = window.speechSynthesis;
    if (!synth || typeof window.SpeechSynthesisUtterance !== 'function') {
      updateNote('ميزة الصوت غير مدعومة في هذا المتصفح. افتح الموقع في Chrome وحدّث الصفحة.');
      return false;
    }
    const utterance = new SpeechSynthesisUtterance(String(text));
    const voices = deviceVoices();
    const saved = localStorage.getItem(voiceKey);
    const voice = voices.find(v => v.voiceURI === saved) || voices[0];
    utterance.lang = voice ? voice.lang : 'ar-SA';
    if (voice) utterance.voice = voice;
    utterance.rate = rate || 0.88;
    utterance.pitch = 1.05;
    utterance.onerror = () => updateNote('تعذر تشغيل صوت الجهاز. تحقق من رفع صوت الوسائط وإعدادات تحويل النص إلى كلام.');
    synth.cancel();
    synth.resume();
    synth.speak(utterance);
    updateNote(voice ? 'يعمل الآن الصوت العربي المتاح في جهازك: ' + voice.name : 'يعمل الآن الصوت العربي الافتراضي في الجهاز.');
    return true;
  }

  function say(text, rate = 0.88) {
    if (!text) return false;
    if (select.value === 'nabra-neural' && typeof window.SmartEduNabraSpeak === 'function') {
      window.SmartEduNabraSpeak(text).then(ok => {
        if (!ok) speakWithDevice(text, rate);
      }).catch(() => speakWithDevice(text, rate));
      return true;
    }
    // Do not leave the learner with silence while the optional neural model is not loaded.
    return speakWithDevice(text, rate);
  }

  select.addEventListener('change', () => {
    mode = select.value === 'nabra-neural' ? 'nabra-neural' : 'device';
    localStorage.setItem(modeKey, mode);
    if (mode === 'device') localStorage.setItem(voiceKey, select.value);
    updateNote();
  });

  if (window.SmartEduVoice) window.SmartEduVoice.speak = say;
  const oldTest = panel.querySelector('#smartVoiceTest') || panel.querySelector('button');
  if (oldTest) {
    const test = oldTest.cloneNode(true);
    oldTest.replaceWith(test);
    test.addEventListener('click', () => say('مَرْحَبًا يا بَطَل! أَنا مُعَلِّمَتُكَ الذَّكِيَّةُ. هَيَّا نَتَعَلَّمُ مَعًا.', 0.88));
  }

  restoreChoice();
  if (window.speechSynthesis) {
    window.speechSynthesis.addEventListener('voiceschanged', () => {
      restoreChoice();
      if (window.SmartEduVoice) window.SmartEduVoice.speak = say;
    });
  }
  // Refresh the voice list after the browser has initialized its speech service.
  setTimeout(() => {
    if (mode === 'device') restoreChoice();
  }, 500);
})();