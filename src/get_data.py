from __future__ import annotations

import base64
import json
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf


DATA_DIR = Path("data/NTRLabMediaSpeech")
ES_ARCHIVE = DATA_DIR / "ES.tgz"
EXTRACT_DIR = DATA_DIR / "extracted"
SRC_SAMPLES_DIR = Path("src/samples")
AUDIO_EXTENSIONS = {".flac", ".wav", ".mp3", ".ogg", ".m4a"}
MEDIA_SPEECH_URL = "https://www.openslr.org/108/"
MEDIA_SPEECH_LICENSE = "CC BY 4.0"
MEDIA_SPEECH_CITATION = """\
@misc{mediaspeech2021,
      title={MediaSpeech: Multilanguage ASR Benchmark and Dataset},
      author={Rostislav Kolobov and Olga Okhapkina and Olga Omelchishina, Andrey Platunov and Roman Bedyakin and Vyacheslav Moshkin and Dmitry Menshikov and Nikolay Mikhaylovskiy},
      year={2021},
      eprint={2103.16193},
      archivePrefix={arXiv},
      primaryClass={eess.AS}
}
"""


def extract_mediaspeech_es(
    archive_path: str | Path = ES_ARCHIVE,
    output_dir: str | Path = EXTRACT_DIR,
    overwrite: bool = False,
) -> Path:
    """Extract the MediaSpeech Spanish tarball and return the extracted ES folder."""
    archive_path = Path(archive_path)
    output_dir = Path(output_dir)

    if not archive_path.exists():
        raise FileNotFoundError(f"Archive not found: {archive_path}")

    es_dir = output_dir / "ES"
    if es_dir.exists() and not overwrite:
        return es_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "r:gz") as tar:
        _safe_extract(tar, output_dir)
    return es_dir


def load_mediaspeech_index(dataset_dir: str | Path = EXTRACT_DIR / "ES") -> pd.DataFrame:
    """Build one row per audio file with duration and sidecar transcription."""
    dataset_dir = Path(dataset_dir)
    if not dataset_dir.exists():
        raise FileNotFoundError(
            f"Dataset folder not found: {dataset_dir}. Run extract_mediaspeech_es first."
        )

    rows = []
    for audio_path in sorted(_iter_audio_files(dataset_dir)):
        text_path = audio_path.with_suffix(".txt")
        rows.append(
            {
                "audio_id": audio_path.stem,
                "audio_path": str(audio_path),
                "text_path": str(text_path) if text_path.exists() else None,
                "relative_path": str(audio_path.relative_to(dataset_dir)),
                "duration_seconds": audio_duration_seconds(audio_path),
                "transcription": read_transcription(text_path) if text_path.exists() else None,
            }
        )

    if not rows:
        raise RuntimeError(f"No audio files found in {dataset_dir}")
    return pd.DataFrame(rows)


def audio_duration_seconds(audio_path: str | Path) -> float:
    """Return audio duration without loading samples into memory."""
    info = sf.info(str(audio_path))
    return float(info.frames / info.samplerate) if info.samplerate else 0.0


def read_transcription(text_path: str | Path) -> str:
    """Read a MediaSpeech sidecar transcription file."""
    return Path(text_path).read_text(encoding="utf-8", errors="replace").strip()


def filter_by_duration(
    index: pd.DataFrame,
    min_seconds: float = 30.0,
    max_seconds: float = 60.0,
) -> pd.DataFrame:
    """Filter samples to the preferred duration window."""
    mask = index["duration_seconds"].between(float(min_seconds), float(max_seconds))
    return index.loc[mask].sort_values("duration_seconds").reset_index(drop=True)


def select_samples(
    index: pd.DataFrame,
    n: int = 5,
    min_seconds: float = 30.0,
    max_seconds: float = 60.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Select a few random samples, preferably in the requested duration range."""
    candidates = filter_by_duration(index, min_seconds=min_seconds, max_seconds=max_seconds)
    if candidates.empty:
        candidates = index.sort_values("duration_seconds").reset_index(drop=True)
    return candidates.sample(n=min(int(n), len(candidates)), random_state=seed).reset_index(drop=True)


def select_sample_bundles(
    index: pd.DataFrame,
    n: int = 3,
    min_seconds: float = 30.0,
    max_seconds: float = 60.0,
    seed: int = 42,
) -> list[pd.DataFrame]:
    """Select groups of real clips whose combined duration is in the target window."""
    shuffled = index.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    bundles: list[pd.DataFrame] = []
    current_rows = []
    current_seconds = 0.0

    for _, row in shuffled.iterrows():
        duration = float(row["duration_seconds"])
        if current_rows and current_seconds + duration > max_seconds:
            if current_seconds >= min_seconds:
                bundles.append(pd.DataFrame(current_rows).reset_index(drop=True))
                if len(bundles) >= int(n):
                    break
            current_rows = []
            current_seconds = 0.0

        current_rows.append(row.to_dict())
        current_seconds += duration

        if current_seconds >= min_seconds:
            bundles.append(pd.DataFrame(current_rows).reset_index(drop=True))
            if len(bundles) >= int(n):
                break
            current_rows = []
            current_seconds = 0.0

    if not bundles and current_rows:
        bundles.append(pd.DataFrame(current_rows).reset_index(drop=True))
    return bundles


def export_bundle_audio(
    bundle: pd.DataFrame,
    output_path: str | Path,
    silence_seconds: float = 0.35,
) -> dict:
    """Concatenate a bundle of clips into one audio file and return its metadata."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    chunks = []
    sample_rate = None
    subtype = None
    for _, row in bundle.iterrows():
        audio, sr = sf.read(row["audio_path"], always_2d=True)
        if sample_rate is None:
            sample_rate = int(sr)
            subtype = sf.info(row["audio_path"]).subtype
        elif int(sr) != sample_rate:
            raise ValueError("All clips in a bundle must share the same sample rate.")

        chunks.append(audio)
        silence_frames = int(round(sample_rate * float(silence_seconds)))
        if silence_frames:
            chunks.append(np.zeros((silence_frames, audio.shape[1]), dtype=audio.dtype))

    combined = np.concatenate(chunks, axis=0)
    sf.write(output_path, combined, sample_rate, subtype=subtype)
    transcription = "\n".join(
        text for text in bundle["transcription"].dropna().astype(str).tolist() if text.strip()
    )
    return {
        "audio_path": str(output_path),
        "duration_seconds": audio_duration_seconds(output_path),
        "clip_count": int(len(bundle)),
        "source_audio_ids": bundle["audio_id"].tolist(),
        "transcription": transcription,
    }


def export_sample_bundles(
    bundles: list[pd.DataFrame],
    output_dir: str | Path = DATA_DIR / "samples",
    prefix: str = "mediaspeech_es",
) -> pd.DataFrame:
    """Write selected bundles to audio files and return an index for listening."""
    records = []
    output_dir = Path(output_dir)
    for i, bundle in enumerate(bundles, start=1):
        output_path = output_dir / f"{prefix}_{i:02d}.flac"
        record = export_bundle_audio(bundle, output_path)
        record["bundle_id"] = f"{prefix}_{i:02d}"
        records.append(record)
    return pd.DataFrame(records)


def persist_sample_bundles(
    bundles: list[pd.DataFrame],
    output_dir: str | Path = SRC_SAMPLES_DIR,
    prefix: str = "mediaspeech_es",
    index_name: str = "index.jsonl",
) -> pd.DataFrame:
    """Persist reusable bundle samples under src/samples with a JSONL index."""
    output_dir = Path(output_dir)
    records = export_sample_bundles(bundles, output_dir=output_dir, prefix=prefix)
    records = records.copy()
    records["audio_path"] = records["audio_path"].map(
        lambda path: Path(path).relative_to(output_dir).as_posix()
    )
    records["dataset"] = "NTRLab MediaSpeech ES"
    records["license"] = MEDIA_SPEECH_LICENSE
    records["source_url"] = MEDIA_SPEECH_URL

    index_path = output_dir / index_name
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("w", encoding="utf-8") as file:
        for record in records.to_dict(orient="records"):
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    return records


def load_persisted_samples(
    samples_dir: str | Path = SRC_SAMPLES_DIR,
    index_name: str = "index.jsonl",
    resolve_paths: bool = True,
    path_column: str = "resolved_audio_path",
) -> pd.DataFrame:
    """Read persisted bundle sample metadata from src/samples."""
    samples_dir = Path(samples_dir)
    index_path = samples_dir / index_name
    if not index_path.exists():
        raise FileNotFoundError(
            f"Sample index not found: {index_path}. Run persist_sample_bundles first."
        )

    records = []
    with index_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    samples = pd.DataFrame(records)
    if samples.empty:
        return samples

    if resolve_paths:
        samples[path_column] = samples["audio_path"].map(
            lambda path: str(samples_dir / Path(*Path(path).parts))
        )
    elif path_column != "audio_path" and "audio_path" in samples.columns:
        samples[path_column] = samples["audio_path"]
    return samples


def mediaspeech_license_info() -> dict:
    """Return dataset citation and attribution information for reports/notebooks."""
    return {
        "dataset": "NTRLab MediaSpeech, Spanish split (ES)",
        "source": MEDIA_SPEECH_URL,
        "license": MEDIA_SPEECH_LICENSE,
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "official_download": "https://www.openslr.org/resources/108/ES.tgz",
        "attribution": (
            "Use with attribution to the MediaSpeech dataset/NTR Labs and include the "
            "OpenSLR source URL. CC BY 4.0 permits sharing and adaptation, including "
            "for commercial use, when appropriate credit is provided."
        ),
        "notes": (
            "OpenSLR describes MediaSpeech as short speech segments automatically "
            "extracted from media videos available on YouTube and manually transcribed. "
            "This project uses locally derived bundle samples created by concatenating "
            "real clips from the Spanish split; keep source_audio_ids in outputs so "
            "samples remain traceable to the original files."
        ),
        "citation": MEDIA_SPEECH_CITATION.strip(),
    }


def display_mediaspeech_license_info() -> dict:
    """Display MediaSpeech citation/license details in a notebook and return them."""
    from IPython.display import Markdown, display

    info = mediaspeech_license_info()
    display(
        Markdown(
            "\n".join(
                [
                    "### Dataset attribution",
                    f"- Dataset: {info['dataset']}",
                    f"- Source: {info['source']}",
                    f"- Official ES download: {info['official_download']}",
                    f"- License: {info['license']} ({info['license_url']})",
                    f"- Attribution: {info['attribution']}",
                    f"- Notes: {info['notes']}",
                    "",
                    "```bibtex",
                    info["citation"],
                    "```",
                ]
            )
        )
    )
    return info


def dataset_summary(index: pd.DataFrame) -> dict:
    """Return compact counts and duration stats for notebook display."""
    preferred = filter_by_duration(index)
    return {
        "samples": int(len(index)),
        "samples_30_60s": int(len(preferred)),
        "hours": round(float(index["duration_seconds"].sum() / 3600), 2),
        "min_seconds": round(float(index["duration_seconds"].min()), 2),
        "median_seconds": round(float(index["duration_seconds"].median()), 2),
        "max_seconds": round(float(index["duration_seconds"].max()), 2),
        "with_transcription": int(index["transcription"].notna().sum()),
    }


def display_audio_sample(row: pd.Series | dict):
    """Display one sample in a notebook with audio and transcription."""
    from IPython.display import HTML, display

    record = dict(row)
    source_path = record.get("resolved_audio_path") or record["audio_path"]
    audio_path = ensure_notebook_wav(source_path)
    audio_data = base64.b64encode(audio_path.read_bytes()).decode("ascii")
    display(HTML(f'<audio controls preload="metadata" src="data:audio/wav;base64,{audio_data}"></audio>'))
    display(pd.DataFrame([record]))
    if record.get("transcription"):
        print(record["transcription"])


def display_samples(samples: pd.DataFrame) -> pd.DataFrame:
    """Display several notebook audio players and return the selected rows."""
    for _, row in samples.iterrows():
        display_audio_sample(row)
    return samples


def ensure_notebook_wav(
    audio_path: str | Path,
    output_dir: str | Path = DATA_DIR / "samples" / "notebook_wav",
) -> Path:
    """Create a WAV preview file for notebook audio widgets when needed."""
    audio_path = Path(audio_path)
    if audio_path.suffix.lower() == ".wav":
        return audio_path

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    wav_path = output_dir / f"{audio_path.stem}.wav"
    if wav_path.exists():
        return wav_path

    audio, sample_rate = sf.read(audio_path, always_2d=True)
    sf.write(wav_path, audio, sample_rate, subtype="PCM_16")
    return wav_path


def _iter_audio_files(dataset_dir: Path):
    return (
        path
        for path in dataset_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )


def _safe_extract(tar: tarfile.TarFile, output_dir: Path) -> None:
    output_root = output_dir.resolve()
    for member in tar.getmembers():
        target = (output_dir / member.name).resolve()
        if output_root != target and output_root not in target.parents:
            raise RuntimeError(f"Unsafe archive member path: {member.name}")
    tar.extractall(output_dir)
