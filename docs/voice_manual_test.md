# Manual Voice Testing Checklist (Web Speech API)

This document provides a manual test plan for verifying voice features in **Google Chrome** and **Microsoft Edge**.

---

## Prerequisites
- A working microphone connected to your computer.
- Google Chrome or Microsoft Edge (Chromium-based).
- Development server running:
  ```powershell
  python run.py
  ```
- A logged-in student user on [http://127.0.0.1:5000/interview/start](http://127.0.0.1:5000/interview/start).

---

## Test Checklist

### 1. Voice Output (Text-to-Speech)
- [ ] **Initial Question Speech:**
  - Start an interview with 3 questions.
  - When Question 1 loads, verify that the browser reads the question aloud in an English voice (`en-IN` or `en-US`).
- [ ] **Autoplay Fallback:**
  - If Chrome blocks autoplay audio on a new page load, verify that the **▶️ Click to hear the question** button appears within ~1 second. Click it to confirm the question is read aloud.
- [ ] **Start Button Disabled During Speech:**
  - While the question is being spoken aloud, verify the **🎙️ Start Answering** button is temporarily disabled.
  - When speech finishes, verify the button enables automatically.
- [ ] **Replay Button:**
  - Click **🔄 Replay Question**. Confirm the question is read aloud again from the beginning.
- [ ] **Mute Button:**
  - Click **🔊 Mute Voice**. Confirm that speech stops immediately, the button label changes to **🔇 Unmute Voice**, and the **Start Answering** button enables immediately.
- [ ] **Page Unload Cleanup:**
  - Start speaking a question, then immediately navigate back or close the tab. Confirm that audio stops immediately without lingering in the background.

---

### 2. Voice Input (Speech-to-Text)
- [ ] **Microphone Permission Prompt:**
  - Click **🎙️ Start Answering**.
  - If prompted, click **Allow** in the browser permission popup.
- [ ] **Listening Status Indicator:**
  - Confirm the status badge updates to **🔴 Listening...** and the button label switches to **⏹️ Stop Answering**.
- [ ] **Live Dictation:**
  - Speak a sentence into your microphone (e.g., *"Object oriented programming uses classes and objects."*).
  - Confirm words appear in real-time in the answer text area.
- [ ] **Silence & Auto-Restart (Chrome Behavior):**
  - Stop speaking for 4–5 seconds.
  - In Chrome, recognition stops on silence; verify the script automatically restarts recognition smoothly so speaking can resume without needing to press Start again.
- [ ] **Pause Tracking (> 3 seconds):**
  - Deliberately pause for 4 seconds between sentences.
  - Verify that the long pause is recorded in the hidden form payload (`long_pause_count`).
- [ ] **Stop & Resume:**
  - Click **⏹️ Stop Answering**.
  - Confirm the status badge updates to **⚪ Not listening** and the button label changes to **🎙️ Resume Answering**.
  - Click **Resume Answering** and speak another sentence; confirm new speech appends to the existing text without overwriting it.

---

### 3. Student Transcript Editing
- [ ] **Manual Text Correction:**
  - Click inside the text area while voice is stopped (or while listening).
  - Edit a typo or add words using your keyboard.
  - Confirm that manual edits remain intact and are not erased by voice events.

---

### 4. Answer Submission & Report Verification
- [ ] **Submit Answer:**
  - Click **Submit Answer & Next →**.
  - Confirm Question 2 loads, speech reads Question 2, and the answer text area is clean and ready.
- [ ] **Complete Interview Session:**
  - Complete the remaining questions using voice (or typed fallback).
  - Submit the final question.
- [ ] **Report Review:**
  - Confirm redirection to `/interview/report/<id>`.
  - Confirm your spoken answers are displayed accurately under **Transcript Summary** with a **Voice** badge.

---

### 5. Fallback & Error Handling
- [ ] **Non-Chromium Browser (e.g. Firefox):**
  - Open the session in Firefox.
  - Verify that the message *"Voice input is optimized for Google Chrome or Microsoft Edge. You can type your answer directly in the box below."* appears.
  - Verify the voice input button is hidden and typing in the text area works normally.
- [ ] **Microphone Blocked:**
  - In Chrome, click the tune/lock icon in the address bar &rarr; Site settings &rarr; set Microphone to **Block**.
  - Reload the page and click **Start Answering**.
  - Verify a friendly alert appears explaining how to unblock microphone permissions.
  - Verify you can still type your answer and submit without issue.

