from pathlib import Path
import torch


MODEL_ID_ASR = 'Qwen/Qwen3-ASR-0.6B'
WORK_DIR_ASR = Path('/content/qwen3-asr-poc')


def choose_dtype():
    if not torch.cuda.is_available():
        return torch.float32
    return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16



def gpu_snapshot():
    if not torch.cuda.is_available():
        return {'gpu': None, 'allocated_mb': None, 'reserved_mb': None, 'max_allocated_mb': None}
    return {
        'gpu': torch.cuda.get_device_name(0),
        'allocated_mb': round(torch.cuda.memory_allocated() / 1024**2, 1),
        'reserved_mb': round(torch.cuda.memory_reserved() / 1024**2, 1),
        'max_allocated_mb': round(torch.cuda.max_memory_allocated() / 1024**2, 1),
    }

def reset_gpu_peak():
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()