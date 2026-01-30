def build_architecture_prompt(question_text, evidence_text):
    prompt = ""

    prompt += "You are a software architecture assistant.\n"
    prompt += "You must answer ONLY using the EVIDENCE block.\n"
    prompt += "For every important statement, add citation.\n"
    prompt += "Do NOT cite anything outside EVIDENCE.\n"
    prompt += "If EVIDENCE is insufficient, say exactly:\n"
    prompt += "I cannot propose a concrete refactoring from the provided evidence.\n"
    prompt += "\n"

    prompt += "QUESTION:\n"
    prompt += question_text.strip() + "\n"
    prompt += "\n"

    prompt += "EVIDENCE:\n"
    prompt += "```text\n"
    prompt += evidence_text.strip() + "\n"
    prompt += "```\n"
    prompt += "\n"

    prompt += "REMINDER:\n"
    prompt += "- Use evidence IDs (CYCLE_k / EDGE_k / MAGNET_k / OVERSIZED_k) exactly as shown in EVIDENCE.\n"
    prompt += "- Break edge must reference exactly one EDGE_k.\n"
    prompt += "- If you reference any file, copy its path verbatim from a *_FILES line in the Context (e.g., MAGNET_k_FILES / CYCLE_k_FILES / EDGE_k_FILES).\n"
    prompt += "- Whenever you mention an existing cycle, edge, magnet, or oversized item, you must cite it using its evidence ID (CYCLE_k / EDGE_k / MAGNET_k / OVERSIZED_k); if it does not exist in the Context, you must prepend [NEW] every time you refer to it."
    return prompt


def build_prompt(query, context_chunks):
    prompt = ""
    prompt += "You must answer ONLY using the provided Context blocks.\n"
    prompt += "For every important statement, add citations like [C1] or [C2].\n"
    prompt += "Do NOT cite anything outside the context.\n"
    prompt += "If the context is insufficient, say: 'I cannot answer from the provided context.'\n\n"

    code_delim = "```"
    i = 1
    for chunk in context_chunks:
        source = chunk.metadata.get("source", chunk.id)
        prompt += "Context " + str(i) + " (from " + str(source) + "):\n"

        if chunk.metadata.get("type") == "code":
            prompt += code_delim + "\n" + chunk.text + "\n" + code_delim + "\n\n"
        else:
            prompt += chunk.text + "\n\n"

        i += 1

    prompt += "Question: " + query + "\n"
    prompt += "Answer:"
    return prompt

