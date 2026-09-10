/* SightMate — voice-first orchestrator.
   One gesture (Enter / click) starts screen sharing; after that the mic stays
   ON continuously — you can talk anytime, and say "stop" to interrupt speech.
   Every question re-reads the LIVE frame, so scrolling is handled automatically. */
(function () {
  const { capture, voice } = window.SightMate;

  let sessionId = null;
  let started = false;
  let speaking = false;
  let pdfMode = false;
  let sharing = false;
  let monitorTimer = null;
  let monitorOn = false;       // is monitoring active?
  let monitorInflight = false; // is a /monitor check currently running?
  let lastAnswer = "";
  let recognizer = null;
  let currentSpeech = ""; // lowercased text we're currently speaking (echo filter)

  const STOP_WORDS = ["stop", "quiet", "cancel", "shut up", "be quiet", "enough"];

  const el = {
    start: document.getElementById("start-btn"),
    status: document.getElementById("status"),
    transcript: document.getElementById("transcript"),
    indicator: document.getElementById("listen-indicator"),
    indicatorLabel: document.getElementById("listen-label"),
    theme: document.getElementById("theme-toggle"),
    pdfBtn: document.getElementById("pdf-btn"),
    pdfInput: document.getElementById("pdf-input"),
    stopBtn: document.getElementById("stop-btn"),
    sampleBanner: document.getElementById("sample-banner"),
  };

  function setStatus(msg) { el.status.textContent = msg; }

  function setIndicator(mode) {
    // mode: "listening" | "speaking" | "off"
    el.indicator.hidden = mode === "off";
    if (mode === "listening") el.indicatorLabel.textContent = "Listening…";
    if (mode === "speaking") el.indicatorLabel.textContent = "Speaking… (say “stop” to interrupt)";
  }

  function addTurn(who, text, kind) {
    const li = document.createElement("li");
    li.className = "turn " + (kind || who);
    const label = document.createElement("span");
    label.className = "who";
    label.textContent = who === "user" ? "You" : "SightMate";
    const body = document.createElement("span");
    body.textContent = text;
    li.appendChild(label);
    li.appendChild(body);
    el.transcript.appendChild(li);
    li.scrollIntoView({ block: "end" });
  }

  // Speak. The recognizer stays on the whole time so "stop" can interrupt.
  function say(text, kind) {
    if (!text) return;
    addTurn("assistant", text, kind || "assistant");
    speaking = true;
    currentSpeech = text.toLowerCase();
    setIndicator("speaking");
    voice.speak(text, function () {
      speaking = false;
      currentSpeech = "";
      setIndicator(started ? "listening" : "off");
    });
  }

  function stopSpeaking(reason) {
    voice.cancel();
    speaking = false;
    currentSpeech = "";
    setStatus(reason || "Stopped.");
    setIndicator(started ? "listening" : "off");
  }

  async function api(path, body) {
    const res = await fetch("/api" + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(function () { return {}; });
    if (!res.ok) throw new Error(data.message || "Request failed.");
    return data;
  }

  // Every recognized phrase (interim + final) comes here.
  function onResult(text, isFinal) {
    const heard = (text || "").toLowerCase();

    if (speaking) {
      // Barge-in: interrupt the instant we hear a stop word — but only if it's
      // NOT part of what we're currently saying (that would be our own echo).
      const userStop = STOP_WORDS.some(function (w) {
        return heard.indexOf(w) !== -1 && currentSpeech.indexOf(w) === -1;
      });
      if (userStop) stopSpeaking("Stopped.");
      return; // ignore everything else while speaking
    }

    if (!isFinal) return; // when not speaking, act only on completed phrases
    const t = (text || "").trim();
    if (!t) return;
    const q = t.toLowerCase();
    const isStop = STOP_WORDS.some(function (w) { return q.indexOf(w) !== -1; }) &&
      q.split(/\s+/).length <= 4;
    handleCommand(t, isStop);
  }

  function handleCommand(t, isStop) {
    addTurn("user", t);
    const q = t.toLowerCase();

    if (isStop) { stopSpeaking("Okay."); return; }
    if (/\b(repeat|again|say that again|what did you say)\b/.test(q)) {
      say(lastAnswer || "I haven't answered anything yet.");
      return;
    }
    if (/\bstop (watching|monitoring|monitor)\b/.test(q)) { stopMonitor(); return; }
    if (/\b(watch|monitor)\b/.test(q)) { startMonitor(); return; }
    ask(t);
  }

  async function ask(question) {
    const useLive = capture.isActive() && !pdfMode;
    const frame = useLive ? capture.grabFrame() : null;

    if (!useLive && !sessionId) { say("Please share your screen first.", "error"); return; }
    setStatus("Thinking…");
    try {
      const body = { session_id: sessionId, question: question };
      if (frame) body.image = frame; // read the CURRENT screen (handles scrolling)
      const data = await api("/ask", body);
      if (data.session_id) sessionId = data.session_id;
      lastAnswer = data.answer;
      setStatus("Ready. Ask me anything about your screen.");
      say(data.answer);
    } catch (err) {
      say(err.message, "error");
    }
  }

  function stopMonitor(announce) {
    monitorOn = false;
    if (monitorTimer) { clearTimeout(monitorTimer); monitorTimer = null; }
    if (announce !== false) say("Stopped watching your screen.");
  }

  function startMonitor() {
    if (!capture.isActive()) { say("Please share your screen first, then I can watch it.", "error"); return; }
    if (monitorOn) { say("I'm already watching your screen."); return; }
    monitorOn = true;
    say("I'll watch your screen and tell you when something important changes.");
    scheduleMonitor(0);
  }

  // Self-scheduling loop: the NEXT check is queued only AFTER the current one
  // finishes, so checks never overlap. This matters on slow models where
  // one check can take a while — a fixed setInterval would stack dozens of
  // in-flight requests and freeze the app.
  function scheduleMonitor(delay) {
    if (!monitorOn) return;
    monitorTimer = setTimeout(pollMonitor, delay);
  }

  async function pollMonitor() {
    if (!monitorOn) return;
    // Don't fire while speaking, not sharing, or a check is already running —
    // but keep the loop alive so it resumes on its own.
    if (speaking || !capture.isActive() || monitorInflight) { scheduleMonitor(2000); return; }
    const frame = capture.grabFrame();
    if (!frame) { scheduleMonitor(2000); return; }

    monitorInflight = true;
    try {
      const data = await api("/monitor", { session_id: sessionId, image: frame });
      const events = data.events || [];
      if (events.length) say(events.join(". "), "event");
      else setStatus("Watching your screen — no important change yet.");
    } catch (err) {
      setStatus("Monitoring error: " + err.message);
    } finally {
      monitorInflight = false;
      scheduleMonitor(2000); // queue the next check now that this one is done
    }
  }

  async function shareScreen() {
    if (sharing) return; // a picker is already open
    sharing = true;
    const firstTime = !started;

    // --- Step 1: share the screen (browser) ---
    let frame;
    try {
      setStatus("Requesting screen access…");
      await capture.start();
      frame = capture.grabFrame();
    } catch (err) {
      let msg;
      if (err && err.code === "insecure-context") {
        msg = "Screen sharing needs a secure page. Please open this at http address localhost, port 5000, not a network address.";
      } else if (err && err.name === "NotAllowedError") {
        msg = "Screen sharing was blocked or cancelled. Press Enter to try again and choose a screen to share.";
      } else if (err && err.name === "NotFoundError") {
        msg = "No screen was available to share.";
      } else {
        msg = "I couldn't start screen sharing. Press Enter to try again.";
      }
      setStatus(msg);
      voice.speak(msg);
      sharing = false;
      return;
    }

    // --- Step 2: send it to the assistant (backend) ---
    try {
      pdfMode = false;
      setStatus("Looking at your screen…");
      const data = await api("/analyze-screen", { image: frame, session_id: sessionId });
      sessionId = data.session_id;
      lastAnswer = data.overview_text;
      started = true;
      el.start.hidden = true;
      el.pdfBtn.hidden = false;
      if (!recognizer) recognizer = voice.startContinuous(onResult); // mic stays on
      setStatus("Ready. Just speak — ask about your screen.");
      say(
        data.overview_text +
          (firstTime
            ? " You can now ask me anything, anytime. Say 'stop' to interrupt me, or 'repeat' to hear that again."
            : "")
      );
    } catch (err) {
      const detail = (err && err.message) ? err.message : "";
      const msg = "I shared your screen but couldn't reach the assistant. Make sure the server is running, then press Enter to try again.";
      setStatus(msg + (detail ? "  (" + detail + ")" : ""));
      voice.speak(msg);
    } finally {
      sharing = false;
    }
  }

  async function analyzeDocument(file) {
    try {
      setStatus("Reading your document…");
      const dataUrl = await new Promise(function (resolve, reject) {
        const r = new FileReader();
        r.onload = function () { resolve(r.result); };
        r.onerror = function () { reject(new Error("Could not read the file.")); };
        r.readAsDataURL(file);
      });
      const data = await api("/analyze-document", { pdf: dataUrl, filename: file.name });
      sessionId = data.session_id;
      lastAnswer = data.overview_text;
      pdfMode = true;
      started = true;
      el.start.hidden = true;
      if (!recognizer) recognizer = voice.startContinuous(onResult);
      setStatus("Document read. Ask me about it.");
      say(data.overview_text + " Ask me anything about this document.");
    } catch (err) {
      say(err.message, "error");
    }
  }

  // --- Wiring ---
  el.start.addEventListener("click", shareScreen);
  if (el.stopBtn) el.stopBtn.addEventListener("click", function () { stopSpeaking("Stopped."); });
  el.pdfBtn.addEventListener("click", function () { el.pdfInput.click(); });

  // Announce (and allow recovery) when the user stops sharing via the browser UI.
  capture.setOnEnded(function () {
    stopMonitor(false); // stop watching without a separate spoken message
    pdfMode = false;
    setStatus("Screen sharing stopped. Press Enter to share again.");
    say("Screen sharing stopped. Press Enter to share your screen again.");
  });
  el.pdfInput.addEventListener("change", function () {
    const f = el.pdfInput.files && el.pdfInput.files[0];
    if (f) analyzeDocument(f);
    el.pdfInput.value = "";
  });

  el.theme.addEventListener("click", function () {
    const order = ["dark", "light", "contrast"];
    const cur = document.documentElement.getAttribute("data-theme") || "dark";
    const next = order[(order.indexOf(cur) + 1) % order.length];
    document.documentElement.setAttribute("data-theme", next);
    setStatus("Theme set to " + next + ".");
  });

  document.addEventListener("keydown", function (e) {
    // Enter always (re)shares the screen — including switching what you share.
    if (e.key === "Enter") { e.preventDefault(); shareScreen(); return; }
    if (!started) return;
    if (e.key === "Escape") { stopSpeaking("Stopped."); }
    else if (e.key === "r" || e.key === "R") { say(lastAnswer || "I haven't answered anything yet."); }
    else if (e.key === "m" || e.key === "M") { monitorOn ? stopMonitor() : startMonitor(); }
  });

  // --- Init ---
  el.start.focus();
  fetch("/api/health")
    .then(function (r) { return r.json(); })
    .then(function (h) { if (h && h.sample_mode) el.sampleBanner.hidden = false; })
    .catch(function () {});
  voice.speak("Welcome to SightMate. Press Enter to share your screen and begin.");
})();
