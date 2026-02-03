import config
import time

from tools.runtime import get_collection
from rag_pipeline.retrieval import retrieve_top_k
from tools.prompt_builder import build_prompt
from tools.llm_client import generate_rag_answer_with_fallback
from tools.verify import verify_citations


def run_question_answering(question, build_index, rebuild_index):
    collection = get_collection(build=build_index, rebuild=rebuild_index)
    if collection is None:
        return None
    
    t0 = time.perf_counter()
    retrieved = retrieve_top_k(collection, question, config.TOP_K)
    t1 = time.perf_counter()
    print("[TIMING] qa_retrieve_ms=" + str(int((t1 - t0) * 1000)))

    prompt = build_prompt(question, retrieved)

    answer = generate_rag_answer_with_fallback(question, retrieved, prompt, verify_citations)
    return answer
