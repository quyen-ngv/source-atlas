from dataclasses import asdict, is_dataclass
from enum import Enum

def convert(obj):
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj):
        return {k: convert(v) for k, v in asdict(obj).items()}
    if isinstance(obj, list):
        return [convert(v) for v in obj]
    if isinstance(obj, dict):
        return {k: convert(v) for k, v in obj.items()}
    return obj