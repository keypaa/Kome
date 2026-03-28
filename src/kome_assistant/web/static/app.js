const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const wakeWordInput = document.getElementById('wakeWord');
const langSelect = document.getElementById('lang');
const statusEl = document.getElementById('status');
const interimEl = document.getElementById('interim');
const finalEl = document.getElementById('final');
const intentEl = document.getElementById('intent');
const historyEl = document.getElementById('history');

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let recognition = null;
let running = false;
let previewTimer = null;

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? 'var(--warn)' : 'var(--good)';
}

function appendHistory(role, text) {
  const item = document.createElement('div');
  item.className = `msg ${role}`;
  item.textContent = `${role}> ${text}`;
  historyEl.prepend(item);
}

function normalize(value) {
  return (value || '').trim().toLowerCase();
}

function extractCommandFromWake(transcript, wakeWord) {
  const raw = (transcript || '').trim();
  if (!raw) {
    return null;
  }
  const wake = normalize(wakeWord);
  if (!wake) {
    return raw;
  }
  const low = raw.toLowerCase();
  const index = low.indexOf(wake);
  if (index < 0) {
    return null;
  }
  const command = raw.slice(index + wake.length).trim().replace(/^[,.:;!?\s]+/, '');
  return command || null;
}

async function fetchJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function scheduleIntentPreview(text) {
  if (previewTimer) {
    clearTimeout(previewTimer);
  }
  previewTimer = setTimeout(async () => {
    try {
      const data = await fetchJson('/api/intent', { text });
      if (data.ok) {
        intentEl.textContent = `intent=${data.intent}\nconfidence=${Number(data.confidence || 0).toFixed(2)}\nlanguage=${data.language}`;
      }
    } catch (error) {
      intentEl.textContent = `intent preview error: ${error}`;
    }
  }, 180);
}

async function runAssistantTurn(command) {
  appendHistory('user', command);
  setStatus('Running assistant turn...');
  try {
    const data = await fetchJson('/api/turn', { text: command });
    if (!data.ok) {
      appendHistory('error', data.error || 'Unknown assistant error');
      setStatus('Assistant turn failed', true);
      return;
    }
    const suffix = data.tool ? ` [tool=${data.tool}]` : '';
    appendHistory('assistant', `${data.reply}${suffix}`);
    setStatus('Listening');
  } catch (error) {
    appendHistory('error', String(error));
    setStatus('Request error', true);
  }
}

function stopRecognition() {
  if (!recognition) {
    return;
  }
  running = false;
  recognition.stop();
  startBtn.disabled = false;
  stopBtn.disabled = true;
  setStatus('Stopped');
}

function startRecognition() {
  if (!SpeechRecognition) {
    setStatus('SpeechRecognition API unavailable in this browser (use Edge/Chrome).', true);
    return;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = langSelect.value;

  recognition.onstart = () => {
    running = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus('Listening');
  };

  recognition.onerror = (event) => {
    setStatus(`Mic error: ${event.error}`, true);
  };

  recognition.onend = () => {
    if (running) {
      recognition.start();
      return;
    }
    startBtn.disabled = false;
    stopBtn.disabled = true;
  };

  recognition.onresult = async (event) => {
    let interim = '';
    let finals = [];

    for (let i = event.resultIndex; i < event.results.length; i += 1) {
      const chunk = event.results[i][0]?.transcript?.trim() || '';
      if (!chunk) {
        continue;
      }
      if (event.results[i].isFinal) {
        finals.push(chunk);
      } else {
        interim += `${chunk} `;
      }
    }

    interim = interim.trim();
    interimEl.textContent = interim || '(no interim text)';

    const wakeWord = wakeWordInput.value;

    if (interim) {
      const maybeCommand = extractCommandFromWake(interim, wakeWord);
      if (maybeCommand) {
        scheduleIntentPreview(maybeCommand);
      } else {
        intentEl.textContent = 'Waiting for wake word in interim speech...';
      }
    }

    for (const finalText of finals) {
      finalEl.textContent = finalText;
      const command = extractCommandFromWake(finalText, wakeWord);
      if (!command) {
        appendHistory('user', `(ignored, wake word not found) ${finalText}`);
        setStatus('Wake word not detected in final segment');
        continue;
      }
      scheduleIntentPreview(command);
      await runAssistantTurn(command);
    }
  };

  recognition.start();
}

startBtn.addEventListener('click', startRecognition);
stopBtn.addEventListener('click', stopRecognition);

setStatus('Idle');
