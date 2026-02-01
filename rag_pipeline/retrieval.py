from rag_pipeline.ingestion import DocumentChunk

def retrieve_top_k(collection, query, top_k, scope="code"):
    if top_k < 1:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where={"type": scope},
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
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else None

        chunk_id = meta.get("source", "")
        chunk = DocumentChunk(chunk_id, doc_text, meta)
        chunk.score = dist
        chunks.append(chunk)

        i += 1

    return chunks
