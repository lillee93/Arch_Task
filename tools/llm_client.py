import re
import requests
import config
import time

def llm_is_available():
    if not config.LM_STUDIO_MODEL:
        return False

    base_url = config.LM_STUDIO_BASE_URL.rstrip("/")
    url = base_url + "/v1/models"
    try:
        r = requests.get(url, timeout=2)
        return r.ok
    except Exception:
        return False


def retrieval_looks_relevant(question, retrieved):
    # Very small lexical check: if nothing in retrieved matches the question terms, treat as unrelated.
    text = question.lower()
    tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", text)

    stop = set([
        "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "by",
        "is", "are", "was", "were", "be", "as", "at", "it", "this", "that", "from",
        "what", "which", "how", "why", "where", "when"
    ])

    useful = []
    for t in tokens:
        if len(t) >= 3 and t not in stop:
            useful.append(t)

    if not useful:
        return True

    best_hits = 0
    for chunk in retrieved:
        chunk_text = chunk.text.lower()
        hits = 0
        for t in useful:
            if t in chunk_text:
                hits += 1
        if hits > best_hits:
            best_hits = hits

    # Minimal threshold: at least 2 matched terms somewhere in top-k
    return best_hits >= 1


def build_fallback_answer(reason, question, retrieved):
    # Keep it safe: do not invent. Provide citations + small evidence pack.
    out = []
    out.append("I cannot answer from the provided context.")
    out.append("")
    out.append("Reason: " + reason)
    out.append("")
    out.append("Retrieved basis:")
    i = 1
    for chunk in retrieved:
        source = chunk.metadata.get("source", chunk.metadata.get("path", "unknown"))
        out.append("- [C" + str(i) + "] " + str(source))
        i += 1

    out.append("")
    out.append("Evidence snippets (for manual inspection):")
    i = 1
    for chunk in retrieved:
        snippet = pick_evidence_snippet(question, chunk.text)
        out.append("[C" + str(i) + "]")
        out.append(snippet)
        out.append("")
        i += 1

    return "\n".join(out)

def generate_rag_answer_with_fallback(question, retrieved, prompt, verify_fn):
    
    if not retrieved:
        return "No relevant retrieval results."

    # Retrieved exists but looks unrelated
    if not retrieval_looks_relevant(question, retrieved):
        answer = build_fallback_answer("retrieval seems unrelated to the question", question, retrieved)
        ok, msg = verify_fn(answer, len(retrieved))
        if not ok:
            return "BLOCKED: " + msg
        return answer

    # LLM down/unconfigured -> fallback
    if not llm_is_available():
        answer = build_fallback_answer("LLM not available", question, retrieved)
        ok, msg = verify_fn(answer, len(retrieved))
        if not ok:
            return "BLOCKED: " + msg
        return answer

    # Try LLM
    start = time.perf_counter()
    answer, err = safe_generate_answer(prompt)
    end = time.perf_counter()
    print("[TIMING] qa_llm_ms=" + str(int((end - start) * 1000)))
    if err:
        answer = build_fallback_answer(err, question, retrieved)

    ok, msg = verify_fn(answer, len(retrieved))
    if not ok:
        return "BLOCKED: " + msg

    return answer

def generate_arch_answer_with_fallback(prompt, evidence, verify_fn):

    if not llm_is_available():
        return build_arch_fallback_answer(evidence, "LLM not available")

    # Try LLM
    start = time.perf_counter()
    answer, err = safe_generate_answer(prompt)
    end = time.perf_counter()
    print("[TIMING] arch_llm_ms=" + str(int((end - start) * 1000)))

    if answer is None:
        return build_arch_fallback_answer(evidence, err)

    # Verify LLM output; if fails
    ok, msg = verify_fn(answer, evidence)
    if not ok:
        return build_arch_fallback_answer(evidence, "verify failed: " + msg)

    return answer


def build_arch_fallback_answer(evidence, reason):
    pick = _pick_first_cycle_and_edge(evidence)
    if pick is None:
        out = []
        out.append("I cannot propose a grounded refactoring from the provided evidence.")
        out.append("")
        out.append("Reason: " + str(reason))
        out.append("")
        out.append("Dependency evidence (raw):")
        out.append(evidence)
        return "\n".join(out)

    cycle_id = pick["cycle_id"]
    cycle_path = pick["cycle_path"]
    edge_id = pick["edge_id"]
    a = pick["edge_a"]
    b = pick["edge_b"]

    out = []
    out.append("Architectural smell: cyclic dependency between packages. [" + cycle_id + "]")
    out.append("")
    out.append("Evidence cycle path: `" + cycle_path + "` [" + cycle_id + "]")
    out.append("Remove edge: " + a + " -> " + b + " [" + edge_id + "]")
    out.append("")
    out.append("Short description of the change:")
    out.append("- Stop " + a + " from depending on " + b + " by introducing an interface (or DTO) that lives in " + a + ". [" + edge_id + "]")
    out.append("- Update " + b + " to implement/consume that interface so the dependency direction becomes one-way (b -> a), not (a -> b). [" + edge_id + "]")
    out.append("")
    out.append("Rationale:")
    out.append("- This breaks the cycle and reduces change ripple across the involved packages. [" + cycle_id + "][" + edge_id + "]")
    out.append("")
    out.append("Expected impact on quality attributes:")
    out.append("- Maintainability: clearer dependency direction and fewer cross-package changes. [" + cycle_id + "]")
    out.append("- Testability: " + a + " can be tested with a stub implementation without pulling in " + b + ". [" + edge_id + "]")
    out.append("")
    out.append("Dependency rule (after): " + a + " must not depend on " + b + ". [" + edge_id + "]")
    out.append("")
    out.append("Note: Fallback used because " + str(reason) + ".")

    return "\n".join(out)


def _pick_first_cycle_and_edge(evidence):
    lines = evidence.splitlines()

    cycle_id = None
    cycle_path = None

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("CYCLE_") and ": " in line:
            cycle_id = line.split(":")[0].strip()
            cycle_path = line[len(cycle_id) + 2 :].strip()
            break
        i += 1

    if cycle_id is None:
        return None

    want = " cycle=" + cycle_id
    edge_id = None
    edge_a = None
    edge_b = None

    j = 0
    while j < len(lines):
        line = lines[j].strip()
        if line.startswith("EDGE_") and want in line and ": " in line:
            edge_id = line.split(":")[0].strip()
            rest = line[len(edge_id) + 2 :].strip()
            left = rest.split(" cycle=")[0].strip()  
            if " -> " in left:
                edge_a = left.split(" -> ")[0].strip()
                edge_b = left.split(" -> ")[1].strip()
                break
        j += 1

    if edge_id is None:
        return None

    return {
        "cycle_id": cycle_id,
        "cycle_path": cycle_path,
        "edge_id": edge_id,
        "edge_a": edge_a,
        "edge_b": edge_b,
    }

def pick_evidence_snippet(question, chunk_text):
    # Find 5 lines around the best matching line; fallback to first 8 lines.
    q_tokens = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", question.lower())

    lines = chunk_text.splitlines()
    if not lines:
        return ""

    best_i = -1
    best_score = 0

    line_index = 0
    for line in lines:
        s = line.lower()
        score = 0
        for t in q_tokens:
            if len(t) >= 3 and t in s:
                score += 1
        if score > best_score:
            best_score = score
            best_i = line_index
        line_index += 1

    if best_i == -1 or best_score == 0:
        # first few lines only
        end = 8
        if len(lines) < end:
            end = len(lines)
        return "\n".join(lines[:end]).strip()

    lo = best_i - 2
    if lo < 0:
        lo = 0
    hi = best_i + 3
    if hi > len(lines):
        hi = len(lines)

    return "\n".join(lines[lo:hi]).strip()


def safe_generate_answer(prompt):
    # Wrap your existing generate_answer(prompt) so we can fallback on any failure.
    try:
        answer = generate_answer(prompt)
        if not answer or not answer.strip():
            return None, "LLM returned empty output"
        return answer, None
    except Exception as e:
        return None, "LLM error: " + str(e)

def generate_answer(prompt):
    base_url = config.LM_STUDIO_BASE_URL.rstrip("/")
    api_url = base_url + "/v1/chat/completions"

    if not config.LM_STUDIO_MODEL:
        raise RuntimeError("Set config.LM_STUDIO_MODEL in config.py to your LM Studio loaded model name.")

    payload = {
        "model": config.LM_STUDIO_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": config.LM_TEMPERATURE,
        "top_p": config.LM_TOP_P
    }
    try:
        r = requests.post(api_url, json=payload, timeout=config.LM_TIMEOUT_SECS)
        r.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to generate answer: {e}")
            
    try:
        data = r.json()
    except Exception as e:
        raise RuntimeError("LM Studio returned non-JSON response: " + str(e))

    if data.get("error"):
        raise RuntimeError("LM Studio API error: " + str(data["error"]))
    
    return data["choices"][0]["message"]["content"]
