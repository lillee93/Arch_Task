import config
from rag_pipeline.ingestion import ingest_repository
from rag_pipeline.embedding import embed_and_store, load_collection


def get_repo_path():
    repo_path = getattr(config, "REPO_PATH", "").strip()
    if not repo_path:
        print("Missing REPO_PATH in rag_pipeline/config.py")
        return None
    return repo_path


def get_collection(build, rebuild):
    """
    - build=True: ingest + embed now (persisted on disk)
    - rebuild=True: delete collection then rebuild
    - build=False: just open persisted collection
    """
    repo_path = get_repo_path()
    if repo_path is None:
        return None

    if rebuild:
        build = True

    if build:
        docs = ingest_repository(repo_path)
        return embed_and_store(docs, reset=rebuild)

    collection = load_collection()
    if collection.count() == 0:
        print("Index is empty. Run with --build to create embeddings.")
        return None

    return collection
