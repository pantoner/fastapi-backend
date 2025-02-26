import os
import json
import faiss
import numpy as np
from collections import defaultdict
try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise RuntimeError("Error importing sentence-transformers. Try updating your requirements.") from e

try:
    from huggingface_hub import cached_download
except ImportError:
    print("⚠️ Warning: `cached_download` not found in `huggingface_hub`. Updating module may be required.")

# ✅ FAISS and Embedding Model Setup
FAISS_INDEX_FILE = "knowledge_index.faiss"
METADATA_FILE = "knowledge_metadata.json"
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# ✅ Load FAISS index
def load_faiss_index():
    if not os.path.exists(FAISS_INDEX_FILE):
        raise RuntimeError("FAISS index file not found! Make sure to embed your data first.")
    return faiss.read_index(FAISS_INDEX_FILE)

# ✅ Load metadata for retrieving text
def load_metadata():
    if not os.path.exists(METADATA_FILE):
        raise RuntimeError("Metadata file not found!")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Load Sentence Transformer Model for Encoding Queries
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
faiss_index = load_faiss_index()
metadata = load_metadata()


def search_faiss(query, top_k=3):
    """Retrieve the most relevant example-based knowledge snippets from FAISS."""
    query_embedding = embedding_model.encode([query], convert_to_numpy=True).astype(np.float32)
    distances, indices = faiss_index.search(query_embedding, top_k)

    grouped_examples = defaultdict(list)
    for dist, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata):
            continue

        entry = metadata[idx]
        if entry.get("chunk_type") == "example":
            topic_path = entry.get("topic_path", "unknown_topic")  # Group by topic
            grouped_examples[topic_path].append(entry["text"])

    # ✅ Merge examples within the same topic path
    merged_results = [". ".join(examples) for examples in grouped_examples.values()]
    
    return merged_results