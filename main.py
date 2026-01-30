import sys

import config
from rag_pipeline.ingestion import ingest_repository
from rag_pipeline.embedding import embed_and_store, load_collection
from rag_pipeline.retrieval import retrieve_top_k
from tools.prompt_builder import build_prompt
from rag_pipeline.llm_client import llm_is_available, safe_generate_answer, retrieval_looks_relevant, build_fallback_answer
from tools.verify import verify_citations

from arch.agent import run_architecture_analysis
from arch.report import write_report


def _get_repo_path():
    repo_path = getattr(config, "REPO_PATH", "").strip()
    if not repo_path:
        print("Missing REPO_PATH in rag_pipeline/config.py")
        return None
    return repo_path


def _get_collection(build, rebuild):
    """
    - build=True: ingest + embed now (persisted on disk)
    - rebuild=True: delete collection then rebuild
    - build=False: just open persisted collection
    """
    repo_path = _get_repo_path()
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


def run_qa(question, build_index, rebuild_index):
    collection = _get_collection(build=build_index, rebuild=rebuild_index)
    if collection is None:
        return

    retrieved = retrieve_top_k(collection, question, config.TOP_K)
    if not retrieved:
        print("No relevant retrieval results.")
        return
    
    # If retrieved exists but looks unrelated, do retrieval-only fallback immediately.
    if not retrieval_looks_relevant(question, retrieved):
        answer = build_fallback_answer("retrieval seems unrelated to the question", question, retrieved)
        ok, msg = verify_citations(answer, len(retrieved))
        if not ok:
            print("BLOCKED:", msg)
            return
        print(answer)
        return
    prompt = build_prompt(question, retrieved)
    print("PROMPT:\n", prompt)

    # If LLM down/unconfigured, fallback.
    if not llm_is_available():
        answer = build_fallback_answer("LLM not available", question, retrieved)
        ok, msg = verify_citations(answer, len(retrieved))
        if not ok:
            print("BLOCKED:", msg)
            return
        print(answer)
        return
    
     # Try LLM; if any error, fallback.
    answer, err = safe_generate_answer(prompt)
    if err:
        answer = build_fallback_answer(err, question, retrieved)

    ok, msg = verify_citations(answer, len(retrieved))
    if not ok:
        print("BLOCKED:", msg)
        return

    print(answer)


def run_arch():
    repo_path = _get_repo_path()
    if repo_path is None:
        return

    answer = run_architecture_analysis(repo_path)
    print(answer)
    write_report("out", answer)


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py build [--rebuild]")
        print('  python main.py qa [--build|--rebuild] <question...>')
        print("  python main.py arch [--build|--rebuild]")
        print("")
        print("Repo path comes from rag_pipeline/config.py: REPO_PATH")
        return

    mode = sys.argv[1].strip()
    args = sys.argv[2:]

    build_index = False
    rebuild_index = False

    while args and args[0].startswith("--"):
        flag = args[0].strip()
        args = args[1:]
        if flag == "--build":
            build_index = True
        elif flag == "--rebuild":
            rebuild_index = True
        else:
            print("Unknown flag:", flag)
            return

    if mode == "build":
        _ = _get_collection(build=True, rebuild=rebuild_index)
        return

    if mode == "qa":
        if not args:
            print("Need a question.")
            return
        question = " ".join(args).strip()
        run_qa(question, build_index=build_index, rebuild_index=rebuild_index)
        return

    if mode == "arch":
        run_arch()
        return

    print("Unknown mode:", mode)


if __name__ == "__main__":
    main()