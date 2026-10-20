import re
import math
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.config import DOCS_DIR, UPLOADS_DIR
from backend.database import get_connection

class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        doc_id: str,
        title: str,
        filename: str,
        doc_type: str,
        date_issued: str,
        effective_date: str,
        valid_until: Optional[str],
        is_active: bool,
        is_conflicting: bool,
        superseded_by_id: Optional[str],
        text: str
    ):
        self.chunk_id = chunk_id
        self.doc_id = doc_id
        self.title = title
        self.filename = filename
        self.doc_type = doc_type
        self.date_issued = date_issued
        self.effective_date = effective_date
        self.valid_until = valid_until
        self.is_active = is_active
        self.is_conflicting = is_conflicting
        self.superseded_by_id = superseded_by_id
        self.text = text
        self.tokens = self._tokenize(text)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r'[a-zA-Z0-9_\-]+', text.lower())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "to", "for", "in", "on", "of", "and", "or",
            "at", "by", "with", "from", "as", "this", "that", "these", "those", "it", "its", "be"
        }
        return [w for w in words if w not in stop_words and len(w) > 1]

class RAGEngine:
    """
    RAG & Knowledge Retrieval Engine.
    Handles semantic and lexical indexing of unstructured documents,
    temporal invalidation (superseded vs active), recency scoring,
    and evidence provenance tracking.
    """

    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.doc_metadata_map: Dict[str, Dict[str, Any]] = {}
        self.idf_cache: Dict[str, float] = {}
        self.reload_index()

    def reload_index(self):
        """Indexes all documents registered in document_metadata table."""
        self.chunks.clear()
        self.doc_metadata_map.clear()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM document_metadata")
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            doc = dict(row)
            self.doc_metadata_map[doc["doc_id"]] = doc
            filepath = DOCS_DIR / doc["filename"]
            if not filepath.exists():
                filepath = UPLOADS_DIR / doc["filename"]

            if filepath.exists():
                try:
                    text = filepath.read_text(encoding="utf-8", errors="ignore")
                    self._create_chunks(doc, text)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

        self._compute_idf()
        print(f"RAG Engine: Indexed {len(self.chunks)} chunks across {len(self.doc_metadata_map)} documents.")

    def _create_chunks(self, doc_meta: Dict[str, Any], text: str, chunk_size: int = 400, overlap: int = 60):
        # Split text into logical paragraphs or sliding chunks
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunk_idx = 0

        for para in paragraphs:
            # If paragraph is within reasonable size, treat as single chunk
            if len(para) <= chunk_size:
                chunk_id = f"{doc_meta['doc_id']}_c{chunk_idx}"
                self.chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_meta["doc_id"],
                    title=doc_meta["title"],
                    filename=doc_meta["filename"],
                    doc_type=doc_meta["doc_type"],
                    date_issued=doc_meta["date_issued"],
                    effective_date=doc_meta["effective_date"],
                    valid_until=doc_meta["valid_until"],
                    is_active=bool(doc_meta["is_active"]),
                    is_conflicting=bool(doc_meta["is_conflicting"]),
                    superseded_by_id=doc_meta["superseded_by_id"],
                    text=para
                ))
                chunk_idx += 1
            else:
                # Subdivide larger paragraphs
                words = para.split()
                sub_chunk = []
                sub_len = 0
                for w in words:
                    sub_chunk.append(w)
                    sub_len += len(w) + 1
                    if sub_len >= chunk_size:
                        c_text = " ".join(sub_chunk)
                        chunk_id = f"{doc_meta['doc_id']}_c{chunk_idx}"
                        self.chunks.append(DocumentChunk(
                            chunk_id=chunk_id,
                            doc_id=doc_meta["doc_id"],
                            title=doc_meta["title"],
                            filename=doc_meta["filename"],
                            doc_type=doc_meta["doc_type"],
                            date_issued=doc_meta["date_issued"],
                            effective_date=doc_meta["effective_date"],
                            valid_until=doc_meta["valid_until"],
                            is_active=bool(doc_meta["is_active"]),
                            is_conflicting=bool(doc_meta["is_conflicting"]),
                            superseded_by_id=doc_meta["superseded_by_id"],
                            text=c_text
                        ))
                        chunk_idx += 1
                        # Retain overlap words
                        overlap_words = sub_chunk[-max(1, int(len(sub_chunk)*0.15)):]
                        sub_chunk = list(overlap_words)
                        sub_len = sum(len(x)+1 for x in sub_chunk)

                if sub_chunk:
                    c_text = " ".join(sub_chunk)
                    chunk_id = f"{doc_meta['doc_id']}_c{chunk_idx}"
                    self.chunks.append(DocumentChunk(
                        chunk_id=chunk_id,
                        doc_id=doc_meta["doc_id"],
                        title=doc_meta["title"],
                        filename=doc_meta["filename"],
                        doc_type=doc_meta["doc_type"],
                        date_issued=doc_meta["date_issued"],
                        effective_date=doc_meta["effective_date"],
                        valid_until=doc_meta["valid_until"],
                        is_active=bool(doc_meta["is_active"]),
                        is_conflicting=bool(doc_meta["is_conflicting"]),
                        superseded_by_id=doc_meta["superseded_by_id"],
                        text=c_text
                    ))
                    chunk_idx += 1

    def _compute_idf(self):
        total_chunks = len(self.chunks)
        if total_chunks == 0:
            return
        df = {}
        for c in self.chunks:
            unique_terms = set(c.tokens)
            for t in unique_terms:
                df[t] = df.get(t, 0) + 1

        self.idf_cache = {
            term: math.log((total_chunks + 1) / (count + 1)) + 1.0
            for term, count in df.items()
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        target_customer_id: Optional[str] = None,
        target_product_sku: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant evidence chunks for quotation context.
        Applies BM25/TF-IDF scoring, domain entity boosting, and temporal recency evaluation.
        """
        if not self.chunks:
            self.reload_index()

        query_tokens = DocumentChunk._tokenize(query)
        if not query_tokens:
            return []

        scored_results = []

        for chunk in self.chunks:
            # 1. Term Matching Score (TF-IDF weighted)
            score = 0.0
            term_freqs = {}
            for t in chunk.tokens:
                term_freqs[t] = term_freqs.get(t, 0) + 1

            for q_term in query_tokens:
                if q_term in term_freqs:
                    tf = term_freqs[q_term] / max(1, len(chunk.tokens))
                    idf = self.idf_cache.get(q_term, 1.5)
                    score += (tf * idf)

            # 2. Domain Entity Boosting
            chunk_lower = chunk.text.lower()
            if target_product_sku and target_product_sku.lower() in chunk_lower:
                score += 2.5
            if target_customer_id and target_customer_id.lower() in chunk_lower:
                score += 2.5

            # Keyword specific boost
            for token in query_tokens:
                if len(token) > 4 and token in chunk_lower:
                    score += 0.4

            # 3. Recency & Temporal Status
            # We don't hide superseded documents, but we score them and tag their validity explicitly
            # so the Copilot can detect outdated information!
            is_superseded = not chunk.is_active or (chunk.superseded_by_id is not None)
            
            # Recency factor based on date_issued
            try:
                doc_dt = datetime.strptime(chunk.date_issued, "%Y-%m-%d")
                # Reference date Oct 2026
                ref_dt = datetime(2026, 10, 19)
                days_old = max(0, (ref_dt - doc_dt).days)
                recency_multiplier = max(0.6, 1.0 - (days_old / 365.0) * 0.4)
            except Exception:
                recency_multiplier = 0.8

            final_score = score * recency_multiplier

            if score > 0.05:
                status_label = "ACTIVE"
                if is_superseded:
                    status_label = "OUTDATED / SUPERSEDED"
                elif chunk.is_conflicting:
                    status_label = "CONFLICT DETECTED"

                scored_results.append({
                    "chunk_id": chunk.chunk_id,
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "filename": chunk.filename,
                    "doc_type": chunk.doc_type,
                    "date_issued": chunk.date_issued,
                    "effective_date": chunk.effective_date,
                    "valid_until": chunk.valid_until,
                    "status": status_label,
                    "is_active": chunk.is_active,
                    "is_superseded": is_superseded,
                    "is_conflicting": chunk.is_conflicting,
                    "superseded_by": chunk.superseded_by_id,
                    "text": chunk.text,
                    "relevance_score": round(final_score, 3)
                })

        # Sort by relevance descending
        scored_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_results[:top_k]

rag_engine = RAGEngine()
