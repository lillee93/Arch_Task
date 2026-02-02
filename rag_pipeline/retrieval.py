import config
import re
from rag_pipeline.ingestion import DocumentChunk


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[^\s]", re.UNICODE)

def truncate_to_max_tokens(text, max_tokens):
    if not text:
        return text

    count = 0
    for m in _TOKEN_RE.finditer(text):
        count += 1
        if count >= max_tokens:
            return text[: m.end()]

    return text

def retrieve_top_k(collection, query, top_k, scope=None):
    if top_k < 1:
        return []
    
    if scope is None:
        scope = config.RETRIEVAL_SCOPE

    if scope == "both":
        where_filter = {"type": {"$in": ["code", "text"]}}
    else:
        where_filter = {"type": scope}

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    chunks = []
    if not results:
        return chunks

    docs_list = results.get("documents")
    metas_list = results.get("metadatas")
    dist_list = results.get("distances")

    if not docs_list or not docs_list[0]:
        return chunks

    docs = docs_list[0]
    metas = metas_list[0] if metas_list and metas_list[0] else [{} for _ in docs]
    dists = dist_list[0] if dist_list and dist_list[0] else [None for _ in docs]

    i = 0
    while i < len(docs):
        doc_text = docs[i]
        doc_text = truncate_to_max_tokens(doc_text, config.MAX_CANDIDATE_TOKENS)
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None

        chunk_id = meta.get("source", "")
        chunk = DocumentChunk(chunk_id, doc_text, meta)
        chunk.score = dist
        chunks.append(chunk)

        i += 1

    return chunks
