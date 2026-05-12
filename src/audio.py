
import base64
import gc
import subprocess
from pathlib import Path
import time

import torch
import librosa

from IPython.display import Audio, Javascript, clear_output, display
from google.colab import files, output


from src import utils


RECORD_JS = """
async function recordAudio(seconds) {
  const stream = await navigator.mediaDevices.getUserMedia({audio: true});
  const mediaRecorder = new MediaRecorder(stream);
  const chunks = [];
  mediaRecorder.ondataavailable = event => chunks.push(event.data);
  mediaRecorder.start();
  await new Promise(resolve => setTimeout(resolve, seconds * 1000));
  await new Promise(resolve => {
    mediaRecorder.onstop = resolve;
    mediaRecorder.stop();
  });
  stream.getTracks().forEach(track => track.stop());
  const blob = new Blob(chunks, {type: 'audio/webm'});
  const reader = new FileReader();
  const dataUrl = await new Promise(resolve => {
    reader.onloadend = () => resolve(reader.result);
    reader.readAsDataURL(blob);
  });
  return dataUrl;
}
"""

def convert_to_wav(audio_path, sample_rate=16000):
    audio_path = Path(audio_path)
    if audio_path.suffix.lower() == '.wav':
        return audio_path
    wav_path = audio_path.with_suffix('.wav')
    subprocess.run(['ffmpeg', '-y', '-i', str(audio_path), '-ac', '1', '-ar', str(sample_rate), str(wav_path)], check=True, capture_output=True)
    return wav_path

def record_audio(seconds=5, out_path=utils.WORK_DIR_ASR / 'recorded.webm'):
    display(Javascript(RECORD_JS))
    data_url = output.eval_js(f'recordAudio({float(seconds)})')
    payload = data_url.split(',', 1)[1]
    out_path = Path(out_path)
    out_path.write_bytes(base64.b64decode(payload))
    return convert_to_wav(out_path)

def save_uploaded_audio(upload_value, out_path=utils.WORK_DIR_ASR / 'uploaded_audio'):
    if not upload_value:
        raise ValueError('Upload an audio file first.')
    item = next(iter(upload_value.values())) if isinstance(upload_value, dict) else upload_value[0]
    name = item.get('metadata', {}).get('name') or item.get('name') or 'uploaded_audio'
    suffix = Path(name).suffix or '.wav'
    out_file = Path(str(out_path) + suffix)
    out_file.write_bytes(item['content'])
    return convert_to_wav(out_file)

def audio_duration_seconds(audio_path):
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    return float(len(y) / sr)