from pathlib import Path

import pandas as pd
import soundfile as sf
from IPython.display import Audio, clear_output, display
from ipywidgets import Button, HBox, IntSlider, Output, VBox

from datasets import load_dataset

from src import utils


DATASET_ID = "BSC-LT/distilled-yodas-spanish"
DEFAULT_SPLIT = "validation_ABR"
DEFAULT_SAMPLE_DIR = utils.WORK_DIR_ASR / "dataset_samples"


def _audio_array_and_rate(audio_value):
    if not audio_value:
        raise ValueError("Dataset row does not contain decoded audio.")
    return audio_value["array"], audio_value["sampling_rate"]


def _persist_dataset_row(row, sample_dir):
    sample_dir = Path(sample_dir)
    sample_dir.mkdir(parents=True, exist_ok=True)

    audio_id = row.get("audio_id") or f"sample_{len(list(sample_dir.glob('*.wav'))):05d}"
    out_path = sample_dir / f"{audio_id}.wav"
    array, sampling_rate = _audio_array_and_rate(row["audio"])
    sf.write(out_path, array, sampling_rate)

    return {
        "audio_id": audio_id,
        "audio_path": str(out_path),
        "duration": float(row.get("duration") or len(array) / sampling_rate),
        "sampling_rate": int(sampling_rate),
        "normalized_text": row.get("normalized_text"),
        "split": row.get("split"),
        "language": row.get("language", "Spanish"),
        "consensus": row.get("consensus"),
        "relative_path": row.get("relative_path"),
    }


def get_dataset_sample(
    split=DEFAULT_SPLIT,
    min_seconds=2.0,
    max_seconds=10.0,
    sample_size=8,
    seed=42,
    cache_dir=None,
    sample_dir=DEFAULT_SAMPLE_DIR,
    shuffle_buffer_size=500,
):
    """Download, length-filter, and persist a small homogeneous ASR sample."""
    dataset = load_dataset(
        DATASET_ID,
        split=split,
        streaming=True,
        cache_dir=cache_dir,
    )
    if shuffle_buffer_size:
        dataset = dataset.shuffle(seed=seed, buffer_size=shuffle_buffer_size)

    records = []
    for row in dataset:
        duration = float(row.get("duration") or 0.0)
        if duration < min_seconds or duration > max_seconds:
            continue
        records.append(_persist_dataset_row(row, sample_dir))
        if len(records) >= sample_size:
            break

    if len(records) < sample_size:
        raise RuntimeError(
            f"Only collected {len(records)} matching samples from {split}; "
            f"requested {sample_size} in [{min_seconds}, {max_seconds}] seconds."
        )
    return records


def sample_to_dataframe(sample_records):
    columns = [
        "audio_id",
        "duration",
        "normalized_text",
        "split",
        "language",
        "consensus",
        "audio_path",
    ]
    return pd.DataFrame(sample_records)[columns]


def explore_sample(sample_records):
    """Render a small notebook explorer for audio and transcriptions."""
    if not sample_records:
        raise ValueError("sample_records is empty.")

    index = IntSlider(value=0, min=0, max=len(sample_records) - 1, step=1, description="Sample")
    previous_button = Button(description="Previous")
    next_button = Button(description="Next")
    out = Output()

    def render():
        record = sample_records[index.value]
        with out:
            clear_output()
            display(Audio(record["audio_path"]))
            display(pd.DataFrame([record]))
            print(record.get("normalized_text") or "")

    def previous(_):
        index.value = max(index.min, index.value - 1)
        render()

    def next_(_):
        index.value = min(index.max, index.value + 1)
        render()

    def changed(_):
        render()

    previous_button.on_click(previous)
    next_button.on_click(next_)
    index.observe(changed, names="value")
    display(VBox([HBox([previous_button, index, next_button]), out]))
    render()
