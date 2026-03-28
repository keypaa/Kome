const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const wakeWordInput = document.getElementById('wakeWord');
const wakeAliasesInput = document.getElementById('wakeAliases');
const langSelect = document.getElementById('lang');
const statusEl = document.getElementById('status');
const interimEl = document.getElementById('interim');
const finalEl = document.getElementById('final');
const intentEl = document.getElementById('intent');
const historyEl = document.getElementById('history');

const TARGET_SAMPLE_RATE = 16000;
const STREAM_CHUNK_SECONDS = 0.6;

let running = false;
let mediaStream = null;
let audioContext = null;
let sourceNode = null;
let processorNode = null;
let pendingPromise = Promise.resolve();
let pcmBuffer = new Float32Array(0);
let streamingEnabled = false;

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

function wakeAliases() {
  return String(wakeAliasesInput.value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

async function fetchJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return response.json();
}

async function refreshConfig() {
  try {
    const data = await fetch('/api/config').then((res) => res.json());
    streamingEnabled = Boolean(data.ok && data.streaming_stt);
    if (data.ok && data.mock_stt) {
      setStatus(`Idle - ${data.stt_backend} active (audio transcription disabled in mock mode)`, true);
      intentEl.textContent = 'Tip: set KOME_STT_MODE=faster-whisper for real microphone transcription.';
      return;
    }
    if (streamingEnabled) {
      setStatus(`Idle - backend streaming STT ready (${data.stt_backend || 'unknown'})`);
    } else {
      setStatus(`Idle - backend will use non-streaming fallback (${data.stt_backend || 'unknown'})`);
    }
  } catch (error) {
    setStatus(`Config check failed: ${error}`, true);
  }
}

function concatFloat32(a, b) {
  const out = new Float32Array(a.length + b.length);
  out.set(a, 0);
  out.set(b, a.length);
  return out;
}

function downsampleTo16k(input, inRate) {
  if (inRate === TARGET_SAMPLE_RATE) {
    return input;
  }
  const ratio = inRate / TARGET_SAMPLE_RATE;
  const outLength = Math.max(1, Math.floor(input.length / ratio));
  const output = new Float32Array(outLength);
  for (let i = 0; i < outLength; i += 1) {
    const idx = Math.floor(i * ratio);
    output[i] = input[Math.min(idx, input.length - 1)];
  }
  return output;
}

function floatToInt16(floatBuffer) {
  const out = new Int16Array(floatBuffer.length);
  for (let i = 0; i < floatBuffer.length; i += 1) {
    const s = Math.max(-1, Math.min(1, floatBuffer[i]));
    out[i] = s < 0 ? s * 32768 : s * 32767;
  }
  return out;
}

function encodeWavPcm16(floatBuffer, sampleRate) {
  const int16 = floatToInt16(floatBuffer);
  const dataBytes = int16.length * 2;
  const buffer = new ArrayBuffer(44 + dataBytes);
  const view = new DataView(buffer);

  const writeString = (offset, text) => {
    for (let i = 0; i < text.length; i += 1) {
      view.setUint8(offset + i, text.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + dataBytes, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, 'data');
  view.setUint32(40, dataBytes, true);

  let offset = 44;
  for (let i = 0; i < int16.length; i += 1) {
    view.setInt16(offset, int16[i], true);
    offset += 2;
  }

  return new Uint8Array(buffer);
}

function toBase64(bytes) {
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    const chunk = bytes.subarray(i, i + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}

function updateIntentPreview(predictedIntent, partialText) {
  if (!predictedIntent) {
    intentEl.textContent = 'Waiting for wake word...';
    return;
  }
  intentEl.textContent = `intent=${predictedIntent}\npreview_text=${partialText || ''}`;
}

function handleStreamResponse(data) {
  if (!data || !data.ok) {
    appendHistory('error', data?.error || 'stream request failed');
    return;
  }

  interimEl.textContent = data.partial_text || '(no interim text)';
  updateIntentPreview(data.predicted_intent, data.processed_text || data.partial_text || '');

  if (!data.actionable || !data.result) {
    return;
  }

  finalEl.textContent = data.result.user_text || '';
  appendHistory('user', data.result.user_text || '(empty user text)');
  appendHistory('assistant', data.result.assistant_text || '(empty assistant text)');
  if (data.metrics) {
    setStatus(`Listening - total ${Number(data.metrics.total_ms || 0).toFixed(0)}ms`);
  }
}

function queueChunkSend(wavBytes, isFinal = false) {
  const payload = {
    wav_base64: wavBytes ? toBase64(wavBytes) : '',
    is_final: isFinal,
  };

  pendingPromise = pendingPromise
    .then(() => fetchJson('/api/stream/chunk', payload))
    .then((data) => {
      handleStreamResponse(data);
    })
    .catch((error) => {
      appendHistory('error', `stream chunk error: ${error}`);
      setStatus('Streaming error', true);
    });
}

function processAudioChunk(inputChunk, inSampleRate) {
  const downsampled = downsampleTo16k(inputChunk, inSampleRate);
  pcmBuffer = concatFloat32(pcmBuffer, downsampled);

  const chunkSamples = Math.floor(STREAM_CHUNK_SECONDS * TARGET_SAMPLE_RATE);
  while (pcmBuffer.length >= chunkSamples) {
    const oneChunk = pcmBuffer.slice(0, chunkSamples);
    pcmBuffer = pcmBuffer.slice(chunkSamples);
    const wavBytes = encodeWavPcm16(oneChunk, TARGET_SAMPLE_RATE);
    queueChunkSend(wavBytes, false);
  }
}

async function startStreaming() {
  if (running) {
    return;
  }

  setStatus('Requesting microphone permission...');

  try {
    await fetchJson('/api/stream/start', {
      wake_word: normalize(wakeWordInput.value),
      wake_aliases: wakeAliases(),
      language: langSelect.value,
    });

    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        channelCount: 1,
      },
    });

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    sourceNode = audioContext.createMediaStreamSource(mediaStream);
    processorNode = audioContext.createScriptProcessor(4096, 1, 1);

    processorNode.onaudioprocess = (event) => {
      if (!running) {
        return;
      }
      const input = event.inputBuffer.getChannelData(0);
      processAudioChunk(new Float32Array(input), audioContext.sampleRate);
    };

    sourceNode.connect(processorNode);
    processorNode.connect(audioContext.destination);

    running = true;
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus('Listening (local streaming STT backend)');
  } catch (error) {
    setStatus(`Mic start failed: ${error}`, true);
    await stopStreaming();
  }
}

async function stopStreaming() {
  if (!running && !mediaStream && !audioContext) {
    return;
  }

  running = false;

  if (pcmBuffer.length > 0) {
    const wavBytes = encodeWavPcm16(pcmBuffer, TARGET_SAMPLE_RATE);
    queueChunkSend(wavBytes, true);
    pcmBuffer = new Float32Array(0);
  } else {
    queueChunkSend(null, true);
  }

  await pendingPromise.catch(() => {});

  try {
    const stopData = await fetchJson('/api/stream/stop', {});
    handleStreamResponse(stopData);
  } catch (error) {
    appendHistory('error', `stream stop error: ${error}`);
  }

  if (processorNode) {
    processorNode.disconnect();
    processorNode.onaudioprocess = null;
    processorNode = null;
  }

  if (sourceNode) {
    sourceNode.disconnect();
    sourceNode = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    await audioContext.close();
    audioContext = null;
  }

  startBtn.disabled = false;
  stopBtn.disabled = true;
  setStatus('Stopped');
}

startBtn.addEventListener('click', () => {
  startStreaming();
});

stopBtn.addEventListener('click', () => {
  stopStreaming();
});

refreshConfig();
