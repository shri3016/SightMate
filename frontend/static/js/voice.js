/* Voice layer — browser Web Speech (STT + TTS).
   Uses ONE continuous recognizer that stays on the whole session (even while
   SightMate is speaking) so the user can interrupt with "stop" at any time. */
(function () {
  window.SightMate = window.SightMate || {};

  const synth = window.speechSynthesis || null;
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition || null;

  function speak(text, onEnd) {
    if (!synth || !text) {
      if (onEnd) onEnd();
      return;
    }
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1.05;
    if (onEnd) {
      u.onend = onEnd;
      u.onerror = onEnd;
    }
    synth.speak(u);
  }

  function cancelSpeech() {
    if (synth) synth.cancel();
  }

  // Start an always-on recognizer. Calls onResult(transcript, isFinal) for every
  // phrase — including interim ones, so "stop" can interrupt speech instantly.
  // Auto-restarts (browsers stop continuous recognition periodically).
  function startContinuous(onResult) {
    if (!SpeechRecognition) return null;
    let stopped = false;
    const rec = new SpeechRecognition();
    rec.lang = "en-US";
    rec.continuous = true;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onresult = function (e) {
      const r = e.results[e.results.length - 1];
      if (onResult) onResult(r[0].transcript, r.isFinal);
    };
    rec.onend = function () {
      if (stopped) return;
      try {
        rec.start();
      } catch (_) {
        setTimeout(function () {
          if (!stopped) { try { rec.start(); } catch (e) {} }
        }, 500);
      }
    };
    rec.onerror = function () {
      /* onend fires next and handles the restart */
    };
    try {
      rec.start();
    } catch (e) {}

    return {
      stop: function () { stopped = true; try { rec.stop(); } catch (e) {} },
    };
  }

  window.SightMate.voice = {
    speak: speak,
    cancel: cancelSpeech,
    startContinuous: startContinuous,
    ttsSupported: !!synth,
    sttSupported: !!SpeechRecognition,
  };
})();
