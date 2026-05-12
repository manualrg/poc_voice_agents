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


def transcribe_audio_batch(asr_model, audio_batch, language=None):
    utils.reset_gpu_peak()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    batch_size = len(audio_batch)
    language_batch = [language] * batch_size if language else None


    started = time.perf_counter()
    results = asr_model.transcribe(audio=audio_batch, language=language_batch)
    latency = time.perf_counter() - started
    return {
        'batch_size': batch_size,
        'latency_seconds': latency,
        'languages': [getattr(r, 'language', None) for r in results],
        'texts': [getattr(r, 'text', str(r)) for r in results],
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


def estimate_stt_cost_from_summary(summary, eur_per_runtime_minute):
    """Convert STT throughput metrics into transcription cost estimates."""
    throughput = summary.get('audio_minutes_processed_per_runtime_minute')
    if not throughput:
        return {
            'eur_per_runtime_minute': float(eur_per_runtime_minute),
            'audio_minutes_processed_per_runtime_minute': throughput,
            'eur_per_transcribed_audio_minute': None,
            'eur_per_transcribed_audio_hour': None,
            'transcribed_audio_minutes_per_eur': None,
        }

    eur_per_audio_minute = float(eur_per_runtime_minute) / float(throughput)
    return {
        'eur_per_runtime_minute': float(eur_per_runtime_minute),
        'audio_minutes_processed_per_runtime_minute': float(throughput),
        'eur_per_transcribed_audio_minute': eur_per_audio_minute,
        'eur_per_transcribed_audio_hour': eur_per_audio_minute * 60,
        'transcribed_audio_minutes_per_eur': 1 / eur_per_audio_minute if eur_per_audio_minute else None,
    }


def summarize_stt_costs(rows_df, eur_per_runtime_minute, include_warmup=False, group_by=('batch_size',)):
    """Summarize measured STT cost globally or grouped by batch size."""
    measured = rows_df.copy()
    if not include_warmup and 'warmup' in measured.columns:
        measured = measured[~measured['warmup']]
    measured = measured[measured['ok']]

    group_columns = list(group_by or [])
    if group_columns:
        grouped = measured.groupby(group_columns, dropna=False)
        records = []
        for group_key, group in grouped:
            record = _stt_cost_record(group, eur_per_runtime_minute)
            if len(group_columns) == 1:
                record[group_columns[0]] = group_key
            else:
                for column, value in zip(group_columns, group_key):
                    record[column] = value
            records.append(record)
        ordered = group_columns + [
            'runs',
            'audio_minutes',
            'runtime_minutes',
            'audio_minutes_processed_per_runtime_minute',
            'eur_per_runtime_minute',
            'eur_per_transcribed_audio_minute',
            'eur_per_transcribed_audio_hour',
        ]
        return pd.DataFrame(records)[ordered]

    return pd.DataFrame([_stt_cost_record(measured, eur_per_runtime_minute)])


def _stt_cost_record(rows_df, eur_per_runtime_minute):
    audio_minutes = float(rows_df['audio_seconds'].sum() / 60)
    runtime_minutes = float(rows_df['latency_seconds'].sum() / 60)
    throughput = audio_minutes / runtime_minutes if runtime_minutes else None
    eur_per_audio_minute = (
        float(eur_per_runtime_minute) / throughput
        if throughput
        else None
    )
    return {
        'runs': int(len(rows_df)),
        'audio_minutes': audio_minutes,
        'runtime_minutes': runtime_minutes,
        'audio_minutes_processed_per_runtime_minute': throughput,
        'eur_per_runtime_minute': float(eur_per_runtime_minute),
        'eur_per_transcribed_audio_minute': eur_per_audio_minute,
        'eur_per_transcribed_audio_hour': eur_per_audio_minute * 60 if eur_per_audio_minute else None,
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
