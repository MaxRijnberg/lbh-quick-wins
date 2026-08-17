from pathlib import Path
from typing import Union

import numpy as np


def cached_encode(model, texts, cache_path: Union[Path, str], **encode_kwargs) -> np.ndarray:
    cache_path = Path(cache_path)
    if cache_path.exists():
        return np.load(cache_path)

    embeddings = model.encode(texts, **encode_kwargs)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, embeddings)
    return embeddings
