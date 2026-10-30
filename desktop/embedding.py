"""CPU-only local BGE inference using CLS pooling, matching SentenceTransformer."""
from __future__ import annotations

import numpy as np
from functools import lru_cache

from desktop.bootstrap import ASSETS


class Embedder:
    def __init__(self):
        from desktop.runtime import asset_check
        from tokenizers import Tokenizer
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        model_path = asset_check("embedding/model_quantized.onnx")
        tokenizer_path = asset_check("embedding/tokenizer.json")
        self.session = ort.InferenceSession(str(model_path),
                                            options, providers=["CPUExecutionProvider"])
        self.tokenizer = Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.enable_truncation(max_length=512)
        self.tokenizer.enable_padding()
        self.names = {item.name for item in self.session.get_inputs()}

    def encode(self, texts):
        batches = []
        for start in range(0, len(texts), 16):
            encodings = self.tokenizer.encode_batch(texts[start:start + 16])
            inputs = {
                "input_ids": np.array([item.ids for item in encodings], dtype=np.int64),
                "attention_mask": np.array([item.attention_mask for item in encodings], dtype=np.int64),
                "token_type_ids": np.array([item.type_ids for item in encodings], dtype=np.int64),
            }
            output = self.session.run(None, {k: v for k, v in inputs.items() if k in self.names})[0]
            vectors = output[:, 0, :] if output.ndim == 3 else output
            batches.append(vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12))
        return np.concatenate(batches).astype(np.float32) if batches else np.empty((0, 384), dtype=np.float32)


@lru_cache(maxsize=1)
def install():
    from matching import embedder
    model = Embedder()
    embedder.available = lambda: True
    embedder.encode = model.encode
    return model
