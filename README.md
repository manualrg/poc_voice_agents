# poc-sst-soa

PoC to try Qwen3 STT and TTS models with Colab.

## Target models

- `Qwen/Qwen3-ASR-0.6B`
- `Qwen/Qwen3-TTS-12Hz-0.6B-Base`

## Deployment

- Google Colab with GPU T4 access.
- STT uses the official `qwen-asr` package.
- TTS uses the official `qwen-tts` package and imports `qwen_tts`.
- Model weights are downloaded from Hugging Face during notebook execution.

Use a Colab GPU runtime before running the model load cells:

```text
Runtime -> Change runtime type -> Hardware accelerator -> T4 GPU
```

## Notebooks

### `01-stt-check-load.ipynb`

- Installs and checks the Colab GPU runtime.
- Loads `Qwen/Qwen3-ASR-0.6B`.
- Provides notebook widgets to record or upload audio and transcribe it.
- Runs configurable load tests over an audio sample.
- Emits STT KPIs: latency, realtime factor, throughput, failure count, and GPU memory.

### `02-tts-check-load.ipynb`

- Installs and checks the Colab GPU runtime.
- Loads `Qwen/Qwen3-TTS-12Hz-0.6B-Base`.
- Provides notebook widgets for text, language, reference audio, reference text, and playback.
- Runs configurable load tests over repeated text prompts.
- Emits TTS KPIs: latency, generated audio throughput, failure count, and GPU memory.

## Cost Translation

The notebooks produce performance KPIs and leave price inputs configurable. To convert a measured run into a cost estimate, provide your own Colab T4 runtime cost:

```text
eur_per_runtime_min = eur_per_runtime_hour / 60
eur_per_audio_min = eur_per_runtime_min / audio_minutes_processed_per_runtime_min
```

For STT, `audio_minutes_processed_per_runtime_min` is based on input audio duration. For TTS, it is based on generated output audio duration.
