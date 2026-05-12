import gc
import time
import statistics
import math

import torch
import pandas as pd

from src import utils, audio

def transcribe_audio(asr_model, audio_path, language=None):
    utils.reset_gpu_peak()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    before = utils.gpu_snapshot()
    started = time.perf_counter()
    results = asr_model.transcribe(audio=str(audio_path), language=language or None)
    latency = time.perf_counter() - started
    after = utils.gpu_snapshot()
    result = results[0]
    duration = audio.audio_duration_seconds(audio_path)
    return {
        'audio_path': str(audio_path),
        'audio_seconds': duration,
        'latency_seconds': latency,
        'realtime_factor': latency / duration if duration else None,
        'language': getattr(result, 'language', None),
        'text': getattr(result, 'text', str(result)),
        'ttfb_seconds': None,
        'gpu_before': before,
        'gpu_after': after,
    }



def percentile(values, p):
    values = sorted(float(v) for v in values if v is not None and not math.isnan(float(v)))
    if not values:
        return None
    idx = (len(values) - 1) * p / 100
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return values[int(idx)]
    return values[lo] + (values[hi] - values[lo]) * (idx - lo)

def summarize_stt_runs(rows):
    successes = [r for r in rows if r['ok']]
    latencies = [r['latency_seconds'] for r in successes]
    total_audio_seconds = sum(r['audio_seconds'] for r in successes)
    total_runtime_seconds = sum(r['latency_seconds'] for r in successes)
    throughput = (total_audio_seconds / 60) / (total_runtime_seconds / 60) if total_runtime_seconds else None
    return {
        'runs': len(rows),
        'successes': len(successes),
        'failures': len(rows) - len(successes),
        'audio_minutes_processed_per_runtime_minute': throughput,
        'mean_latency_seconds': statistics.mean(latencies) if latencies else None,
        'p50_latency_seconds': percentile(latencies, 50),
        'p90_latency_seconds': percentile(latencies, 90),
        'p95_latency_seconds': percentile(latencies, 95),
        'mean_realtime_factor': statistics.mean([r['realtime_factor'] for r in successes]) if successes else None,
        'ttfb_seconds': 'N/A - offline package call returns only the final result',
        'gpu_memory_after': utils.gpu_snapshot(),
    }

def _sample_records(audio_source):
    if isinstance(audio_source, (str, bytes)) or hasattr(audio_source, "__fspath__"):
        audio_path = str(audio_source)
        return [{
            "audio_path": audio_path,
            "audio_seconds": audio.audio_duration_seconds(audio_path),
            "audio_id": None,
            "reference_text": None,
        }]

    records = []
    for index, item in enumerate(audio_source):
        audio_path = item.get("audio_path") or item.get("path")
        if not audio_path:
            raise ValueError(f"Sample record {index} does not contain audio_path.")
        duration = item.get("duration") or item.get("audio_seconds") or audio.audio_duration_seconds(audio_path)
        records.append({
            "audio_path": str(audio_path),
            "audio_seconds": float(duration),
            "audio_id": item.get("audio_id"),
            "reference_text": item.get("normalized_text") or item.get("reference_text"),
        })
    if not records:
        raise ValueError("audio_source did not contain any samples.")
    return records


def transcribe_audio_batch(asr_model, audio_source, batch_size=1, language=None):
    utils.reset_gpu_peak()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    records = _sample_records(audio_source)
    selected = records[: int(batch_size)]
    duration = sum(record["audio_seconds"] for record in selected)
    audio_batch = [record["audio_path"] for record in selected]
    language_batch = [language] * len(selected) if language else None
    started = time.perf_counter()
    results = asr_model.transcribe(audio=audio_batch, language=language_batch)
    latency = time.perf_counter() - started
    return {
        'batch_size': len(selected),
        'audio_ids': [record["audio_id"] for record in selected],
        'reference_texts': [record["reference_text"] for record in selected],
        'audio_seconds': duration,
        'latency_seconds': latency,
        'realtime_factor': latency / duration if duration else None,
        'languages': [getattr(r, 'language', None) for r in results],
        'texts': [getattr(r, 'text', str(r)) for r in results],
    }

def run_stt_load_test(asr_model, audio_source, repeats=5, warmup_runs=1, batch_sizes=None, language="Spanish"):
    batch_sizes = batch_sizes or [1]
    records = _sample_records(audio_source)
    rows = []
    for batch_size in batch_sizes:
        for i in range(warmup_runs + repeats):
            is_warmup = i < warmup_runs
            offset = (i * int(batch_size)) % len(records)
            selected = [records[(offset + j) % len(records)] for j in range(int(batch_size))]
            try:
                result = transcribe_audio_batch(asr_model, selected, batch_size=batch_size, language=language)
                rows.append({
                    'batch_size': int(batch_size),
                    'run': i + 1,
                    'warmup': is_warmup,
                    'ok': True,
                    'audio_ids': '|'.join([str(x) for x in result['audio_ids']]),
                    'audio_seconds': result['audio_seconds'],
                    'latency_seconds': result['latency_seconds'],
                    'realtime_factor': result['realtime_factor'],
                    'ttfb_seconds': None,
                    'language': ','.join([str(x) for x in result['languages']]),
                    'reference_text': ' | '.join([str(x) for x in result['reference_texts']]),
                    'prediction_text': ' | '.join([str(x) for x in result['texts']]),
                    'error': None,
                })
            except Exception as exc:
                rows.append({'batch_size': int(batch_size), 'run': i + 1, 'warmup': is_warmup, 'ok': False, 'audio_ids': None, 'audio_seconds': None, 'latency_seconds': None, 'realtime_factor': None, 'ttfb_seconds': None, 'language': None, 'reference_text': None, 'prediction_text': None, 'error': repr(exc)})
    measured = [r for r in rows if not r['warmup']]
    return pd.DataFrame(rows), summarize_stt_runs(measured)
