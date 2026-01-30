# ingestion.py
import os

class DocumentChunk:
    def __init__(self, chunk_id, text, metadata):
        self.id = chunk_id
        self.text = text
        self.metadata = metadata
        self.score = None  # filled during retrieval if needed


def ingest_repository(repo_path):
    documents = []

    # 1) README.md (paragraph chunks)
    readme_path = os.path.join(repo_path, "README.md")
    if os.path.isfile(readme_path):
        try:
            f = open(readme_path, "r", encoding="utf-8", errors="ignore")
            readme_text = f.read()
            f.close()
        except Exception:
            readme_text = ""

        paragraphs = []
        for para in readme_text.split("\n\n"):
            p = para.strip()
            if p:
                paragraphs.append(p)

        idx = 1
        for para in paragraphs:
            chunk_id = "README_paragraph_" + str(idx)
            metadata = {"source": "README.md", "type": "text"}
            documents.append(DocumentChunk(chunk_id, para, metadata))
            idx += 1

    # 2) Java files (whole-file chunks)
    for root, _, files in os.walk(repo_path):
        for name in files:
            if not name.endswith(".java"):
                continue

            file_path = os.path.join(root, name)
            try:
                f = open(file_path, "r", encoding="utf-8", errors="ignore")
                code = f.read().strip()
                f.close()
            except Exception:
                continue

            if not code:
                continue

            rel_path = os.path.relpath(file_path, repo_path)
            rel_path = rel_path.replace(os.sep, "/")

            # Always exclude tests
            if rel_path.startswith("src/test/"):
                continue

            class_name = name[:-5]  # drop ".java"
            metadata = {"source": rel_path, "type": "code", "class": class_name}

            documents.append(DocumentChunk(rel_path, code, metadata))
    return documents
