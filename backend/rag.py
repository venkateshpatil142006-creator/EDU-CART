import io
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
    # Simple keyword/overlap retrieval for RAG
    if not materials_content:
        return ""
    
    query_words = set(query.lower().split())
    scored_chunks = []
    
    for content in materials_content:
        chunks = chunk_text(content)
        for chunk in chunks:
            chunk_words = set(chunk.lower().split())
            overlap = len(query_words.intersection(chunk_words))
            scored_chunks.append((overlap, chunk))
            
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [c[1] for c in scored_chunks[:top_k] if c[0] > 0]
    
    if not top_chunks and materials_content:
        # Fallback to first few chunks of first material
        top_chunks = chunk_text(materials_content[0])[:top_k]
        
    return "\n---\n".join(top_chunks)
