/**
 * interview_voice.js
 * 
 * Handles voice interactions for the BCA Mock Interview application:
 * 1. Text-to-Speech (TTS) using window.speechSynthesis to read interview questions.
 * 2. Speech-to-Text (STT) using Web Speech API (SpeechRecognition) for answer dictation.
 * 3. Chrome silence auto-restart, pause detection (>3s), and timing measurement.
 * 4. Graceful fallbacks so typed answers always work.
 */

document.addEventListener("DOMContentLoaded", function () {
  // DOM Elements
  const questionTextElem = document.getElementById("question-text");
  const transcriptTextarea = document.getElementById("transcript");
  const form = document.querySelector("form");

  // Voice output controls
  const btnReplay = document.getElementById("btn-replay-question");
  const btnMute = document.getElementById("btn-mute-toggle");
  const btnHearQuestion = document.getElementById("btn-hear-question");

  // Voice input controls
  const btnToggleVoice = document.getElementById("btn-toggle-voice");
  const listeningBadge = document.getElementById("listening-badge");
  const voiceFallbackMsg = document.getElementById("voice-fallback-msg");
  const voiceErrorNotice = document.getElementById("voice-error-notice");

  // Hidden form fields
  const inputMethodField = document.getElementById("input_method");
  const durationField = document.getElementById("speech_duration_ms");
  const pauseCountField = document.getElementById("long_pause_count");

  // State flags
  let isSpeaking = false;
  let isMuted = false;
  let isRecording = false;
  let isManualStop = false;

  // Timing and metric tracking
  let speechStartTime = null;
  let totalSpeechDurationMs = 0;
  let lastResultTimestamp = null;
  let longPauseCount = 0;
  const LONG_PAUSE_THRESHOLD_MS = 3000; // 3 seconds

  // Transcript tracking
  let baseText = "";
  let finalTranscript = "";

  /* =========================================================================
     1. Text-to-Speech (Voice Output)
     ========================================================================= */

  let availableVoices = [];

  function loadVoices() {
    if ("speechSynthesis" in window) {
      availableVoices = window.speechSynthesis.getVoices();
    }
  }

  // Voices may load asynchronously in Chrome/Edge
  if ("speechSynthesis" in window) {
    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;
  }

  function getPreferredVoice() {
    if (!availableVoices.length) {
      availableVoices = window.speechSynthesis.getVoices();
    }
    // Prefer Indian English or US English voices
    return (
      availableVoices.find((v) => v.lang === "en-IN") ||
      availableVoices.find((v) => v.lang === "en-US") ||
      availableVoices.find((v) => v.lang.startsWith("en")) ||
      null
    );
  }

  function speakQuestion() {
    if (!("speechSynthesis" in window) || !questionTextElem) {
      enableVoiceInputButton();
      return;
    }

    if (isMuted) {
      enableVoiceInputButton();
      return;
    }

    // Cancel any active utterance first
    window.speechSynthesis.cancel();

    const textToSpeak = questionTextElem.textContent.trim();
    if (!textToSpeak) {
      enableVoiceInputButton();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(textToSpeak);
    utterance.rate = 0.95; // Slightly slower, clear pace for freshers
    utterance.pitch = 1.0;

    const voice = getPreferredVoice();
    if (voice) {
      utterance.voice = voice;
      utterance.lang = voice.lang;
    } else {
      utterance.lang = "en-US";
    }

    utterance.onstart = function () {
      isSpeaking = true;
      if (btnHearQuestion) btnHearQuestion.style.display = "none";
      if (btnReplay) btnReplay.disabled = true;
      disableVoiceInputButton("Listening to question...");
    };

    utterance.onend = function () {
      isSpeaking = false;
      if (btnReplay) btnReplay.disabled = false;
      enableVoiceInputButton();
    };

    utterance.onerror = function () {
      isSpeaking = false;
      if (btnReplay) btnReplay.disabled = false;
      enableVoiceInputButton();
    };

    // Autoplay check: If browser blocks autoplay, show the explicit hear button
    setTimeout(function () {
      if (!isSpeaking && !isMuted && window.speechSynthesis.speaking === false) {
        if (btnHearQuestion) {
          btnHearQuestion.style.display = "inline-flex";
        }
        enableVoiceInputButton();
      }
    }, 1000);

    window.speechSynthesis.speak(utterance);
  }

  function disableVoiceInputButton(reason) {
    if (btnToggleVoice) {
      btnToggleVoice.disabled = true;
      btnToggleVoice.title = reason || "Question is being read aloud";
    }
  }

  function enableVoiceInputButton() {
    if (btnToggleVoice) {
      btnToggleVoice.disabled = false;
      btnToggleVoice.title = "Click to answer via microphone";
    }
  }

  // Replay question event
  if (btnReplay) {
    btnReplay.addEventListener("click", function () {
      if (isRecording) {
        stopVoiceRecognition();
      }
      speakQuestion();
    });
  }

  // Mute toggle event
  if (btnMute) {
    btnMute.addEventListener("click", function () {
      isMuted = !isMuted;
      btnMute.textContent = isMuted ? "🔇 Unmute Voice" : "🔊 Mute Voice";
      if (isMuted) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
        enableVoiceInputButton();
      }
    });
  }

  // Explicit "Click to hear question" button if autoplay blocked
  if (btnHearQuestion) {
    btnHearQuestion.addEventListener("click", function () {
      btnHearQuestion.style.display = "none";
      speakQuestion();
    });
  }

  // Cancel speech on page exit
  window.addEventListener("beforeunload", function () {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }
  });

  /* =========================================================================
     2. Speech-to-Text (Voice Input)
     ========================================================================= */

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SpeechRecognition) {
    // Browser does not support speech recognition (e.g. Firefox)
    if (voiceFallbackMsg) voiceFallbackMsg.style.display = "block";
    if (btnToggleVoice) btnToggleVoice.style.display = "none";
    if (listeningBadge) listeningBadge.style.display = "none";
  } else {
    const recognition = new SpeechRecognition();
    recognition.lang = "en-IN";
    recognition.continuous = true;
    recognition.interimResults = true;

    function startVoiceRecognition() {
      if (isSpeaking) {
        window.speechSynthesis.cancel();
        isSpeaking = false;
      }

      isRecording = true;
      isManualStop = false;
      speechStartTime = Date.now();
      lastResultTimestamp = Date.now();

      // Snapshot any existing text in the textarea so user edits are preserved
      baseText = transcriptTextarea.value.trim();
      if (baseText.length > 0) {
        baseText += " ";
      }
      finalTranscript = "";

      // UI state
      btnToggleVoice.textContent = "⏹️ Stop Answering";
      btnToggleVoice.classList.add("btn-danger");
      btnToggleVoice.classList.remove("btn-primary");
      listeningBadge.style.display = "inline-flex";
      listeningBadge.textContent = "🔴 Listening...";
      listeningBadge.className = "listening-badge active";

      // Mark input method
      if (inputMethodField) inputMethodField.value = "voice";

      try {
        recognition.start();
      } catch (err) {
        // Recognition might already be running
      }
    }

    function stopVoiceRecognition() {
      isRecording = false;
      isManualStop = true;

      if (speechStartTime) {
        totalSpeechDurationMs += (Date.now() - speechStartTime);
        speechStartTime = null;
      }

      // Update hidden inputs
      if (durationField) durationField.value = totalSpeechDurationMs;
      if (pauseCountField) pauseCountField.value = longPauseCount;

      try {
        recognition.stop();
      } catch (err) {}

      // UI state
      btnToggleVoice.textContent = "🎙️ Resume Answering";
      btnToggleVoice.classList.remove("btn-danger");
      btnToggleVoice.classList.add("btn-primary");
      listeningBadge.style.display = "inline-flex";
      listeningBadge.textContent = "⚪ Not listening";
      listeningBadge.className = "listening-badge inactive";
    }

    btnToggleVoice.addEventListener("click", function () {
      if (isRecording) {
        stopVoiceRecognition();
      } else {
        startVoiceRecognition();
      }
    });

    // Handle recognition speech results
    recognition.onresult = function (event) {
      const now = Date.now();

      // Measure pause duration since last result
      if (lastResultTimestamp !== null) {
        const gap = now - lastResultTimestamp;
        if (gap >= LONG_PAUSE_THRESHOLD_MS) {
          longPauseCount++;
          if (pauseCountField) pauseCountField.value = longPauseCount;
        }
      }
      lastResultTimestamp = now;

      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; ++i) {
        const transcriptPart = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcriptPart + " ";
        } else {
          interim += transcriptPart;
        }
      }

      // Live transcript update in text area (student can still edit manually)
      transcriptTextarea.value = baseText + finalTranscript + interim;
    };

    // Chrome stops recognition after silence. Auto-restart if student didn't press Stop.
    recognition.onend = function () {
      if (isRecording && !isManualStop) {
        try {
          recognition.start();
        } catch (e) {}
      }
    };

    // Friendly error handling
    recognition.onerror = function (event) {
      if (event.error === "no-speech") {
        // Normal silence timeout; auto-restart will handle this smoothly
        return;
      }

      if (event.error === "not-allowed") {
        showErrorNotice(
          "Microphone permission was denied. Please allow microphone access in your browser address bar to use voice input, or type your answer directly."
        );
        stopVoiceRecognition();
      } else if (event.error === "audio-capture") {
        showErrorNotice(
          "No microphone found on your device. You can type your answer in the box below."
        );
        stopVoiceRecognition();
      } else if (event.error === "network") {
        showErrorNotice(
          "Network issue with the speech recognition service. You can continue typing your answer."
        );
        stopVoiceRecognition();
      }
    };
  }

  function showErrorNotice(msg) {
    if (voiceErrorNotice) {
      voiceErrorNotice.textContent = msg;
      voiceErrorNotice.style.display = "block";
    }
  }

  /* =========================================================================
     3. Form Submission Finalization
     ========================================================================= */

  if (form) {
    form.addEventListener("submit", function () {
      // If voice recognition is still active when user clicks submit, accumulate duration
      if (isRecording && speechStartTime) {
        totalSpeechDurationMs += (Date.now() - speechStartTime);
        isRecording = false;
      }

      if (durationField) {
        durationField.value = totalSpeechDurationMs;
      }
      if (pauseCountField) {
        pauseCountField.value = longPauseCount;
      }

      // If text was modified or voice was never used, check input_method
      if (totalSpeechDurationMs <= 0 && inputMethodField && inputMethodField.value !== "voice") {
        inputMethodField.value = "typed";
      }

      // Cancel speech on submit
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    });
  }

  // Kick off initial question speech
  speakQuestion();
});

