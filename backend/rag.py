import io
import re
import math
from typing import List
from pypdf import PdfReader

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    if filename.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    text += t + "\n"
            return text
        except Exception as e:
            return f"Error parsing PDF: {str(e)}"
    else:
        try:
            return file_content.decode("utf-8", errors="ignore")
        except Exception:
            return "Unable to decode text file."

def chunk_text(text: str, chunk_size: int = 500) -> List[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks if chunks else [text]

def retrieve_relevant_context(query: str, materials_content: List[str], top_k: int = 3) -> str:
    if not materials_content:
        return ""

    stop_words = {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with"}
    query_words = {
        word for word in re.findall(r"[a-z0-9_+#.-]+", query.lower())
        if word not in stop_words and len(word) > 1
    }
    if not query_words:
        return ""

    scored_chunks = []

    for content in materials_content:
        chunks = chunk_text(content)
        for chunk in chunks:
            tokens = re.findall(r"[a-z0-9_+#.-]+", chunk.lower())
            token_set = set(tokens)
            overlap = query_words.intersection(token_set)
            if not overlap:
                continue
            frequency = sum(tokens.count(word) for word in overlap)
            coverage = len(overlap) / len(query_words)
            phrase_bonus = 1 if query.lower() in chunk.lower() else 0
            score = coverage + math.log1p(frequency) * 0.15 + phrase_bonus
            scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)
    return "\n---\n".join(chunk for _, chunk in scored_chunks[:top_k])
