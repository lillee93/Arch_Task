# llm_client.py
import re
import requests
import config

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
        return True  # don't block if question is too short / generic

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
    return best_hits >= 2


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
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to generate answer: {e}")
            
    data = r.json()

    if data.get("error"):
        raise RuntimeError(f"LM Studio API error: {data['error']}")
    
    return data["choices"][0]["message"]["content"]
