/* Screen capture — browser getDisplayMedia.
   Holds the shared stream and grabs a single JPEG frame on demand. */
(function () {
  window.SightMate = window.SightMate || {};

  let stream = null;
  let onEndedCb = null;
  const video = document.createElement("video");
  video.muted = true;

  async function start() {
    // getDisplayMedia only exists on a secure context (https or localhost).
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      const e = new Error("insecure-context");
      e.code = "insecure-context";
      throw e;
    }
    // Stop any previous share before starting a new one (re-share support).
    // Calling stop() does not fire the "ended" event, so onEndedCb is safe.
    if (stream) {
      stream.getTracks().forEach(function (t) { t.stop(); });
      stream = null;
    }
    stream = await navigator.mediaDevices.getDisplayMedia({
      video: { frameRate: 1 },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    // Fires only when the USER stops sharing via the browser UI.
    stream.getVideoTracks()[0].addEventListener("ended", function () {
      stream = null;
      if (onEndedCb) onEndedCb();
    });
    return true;
  }

  function isActive() {
    return !!stream && stream.active;
  }

  // Returns a base64 JPEG data URL of the current frame, or null.
  // Downscaled to ~1280px wide → fewer image tokens → faster + cheaper answers.
  function grabFrame() {
    if (!isActive() || !video.videoWidth) return null;
    const maxW = 1280;
    const scale = Math.min(1, maxW / video.videoWidth);
    const w = Math.round(video.videoWidth * scale);
    const h = Math.round(video.videoHeight * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.6);
  }

  window.SightMate.capture = {
    start: start,
    grabFrame: grabFrame,
    isActive: isActive,
    setOnEnded: function (fn) { onEndedCb = fn; },
  };
})();
