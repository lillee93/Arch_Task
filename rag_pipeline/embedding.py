
import os
import chromadb
from chromadb.utils import embedding_functions

import config


def _make_embedding_fn():
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL_NAME
    )


def _open_persistent_collection():
    os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)

    client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
    collection = client.get_or_create_collection(
        name=config.CHROMA_COLLECTION_NAME,
        embedding_function=_make_embedding_fn(),
        metadata={"hnsw:space": config.CHROMA_SPACE},
    )
    return client, collection


def load_collection():
    """
    Open the persisted collection without rebuilding.
    """
    _, collection = _open_persistent_collection()
    return collection


def embed_and_store(documents, reset=False):
    """
    Build (or rebuild) the persisted index.
    - reset=True deletes the collection then recreates it.
    - uses upsert to avoid 'id already exists' errors.
    """
    client, collection = _open_persistent_collection()

    if reset:
        try:
            client.delete_collection(name=config.CHROMA_COLLECTION_NAME)
        except Exception:
            pass

        collection = client.create_collection(
            name=config.CHROMA_COLLECTION_NAME,
            embedding_function=_make_embedding_fn(),
            metadata={"hnsw:space": config.CHROMA_SPACE},
        )

    texts, ids, metadatas = [], [], []
    for doc in documents:
        texts.append(doc.text)
        ids.append(doc.id)
        metadatas.append(doc.metadata)

    # Prefer upsert (safe for rebuilds); fallback to add
    if hasattr(collection, "upsert"):
        collection.upsert(documents=texts, metadatas=metadatas, ids=ids)
    else:
        collection.add(documents=texts, metadatas=metadatas, ids=ids)

    print("Chroma persist dir:", config.CHROMA_PERSIST_DIR)
    print("Chroma collection:", config.CHROMA_COLLECTION_NAME)
    print("Chroma count:", collection.count())
    return collection