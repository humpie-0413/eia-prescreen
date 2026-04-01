"""환경영향평가서 RAG(Retrieval-Augmented Generation) 서비스.

ChromaDB + sentence-transformers로 실제 평가서 원문을 벡터 검색하고,
DeepSeek V3로 근거 기반 답변을 생성한다.

사용:
    rag = ReportRAG()
    rag.load()                        # 색인 로드
    rag.index_reports()               # 추출된 보고서 색인
    result = await rag.query("도로 사업 비산먼지 저감방안은?")
    result = await rag.draft_assist("대기질", "road", risk_cards)
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXTRACTED_DIR = _PROJECT_ROOT / "data" / "reports" / "extracted"
CHROMA_DIR = _PROJECT_ROOT / "data" / "reports" / "chromadb"
COLLECTION_NAME = "eia_reports"

_DISCLAIMER = "이 답변은 실제 환경영향평가서 원문을 참조한 AI 생성 결과이며, 참고용입니다."

# 청킹 설정
CHUNK_SIZE = 500  # 대략적 토큰 수 (한국어 기준 글자 수 ≈ 토큰 수)
CHUNK_OVERLAP = 50


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """텍스트를 청크 단위로 분할한다.

    문단 경계를 우선 존중하고, 긴 문단은 문장 단위로 자른다.
    """
    if not text or not text.strip():
        return []

    # 문단 분리
    paragraphs = re.split(r"\n{2,}", text.strip())
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 현재 청크에 추가해도 크기를 초과하지 않으면 추가
        if len(current_chunk) + len(para) + 1 <= chunk_size:
            current_chunk = f"{current_chunk}\n{para}" if current_chunk else para
        else:
            # 현재 청크 저장
            if current_chunk:
                chunks.append(current_chunk)

            # 문단 자체가 청크 크기를 초과하면 문장 단위로 분할
            if len(para) > chunk_size:
                sentences = re.split(r"(?<=[.!?。])\s+", para)
                sub_chunk = ""
                for sent in sentences:
                    if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                        sub_chunk = f"{sub_chunk} {sent}" if sub_chunk else sent
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = sent
                current_chunk = sub_chunk
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    # overlap 적용: 인접 청크 끝/시작을 겹침
    if overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-overlap:]
            overlapped.append(f"{prev_tail} {chunks[i]}")
        chunks = overlapped

    return chunks


class ReportRAG:
    """환경영향평가서 RAG 서비스."""

    def __init__(self) -> None:
        self._collection = None
        self._embed_model = None
        self._loaded = False

    def load(self) -> None:
        """ChromaDB 컬렉션과 임베딩 모델을 로드한다."""
        if self._loaded:
            return

        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            CHROMA_DIR.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB 로드 완료 (컬렉션: %s, 문서 수: %d)",
                COLLECTION_NAME,
                self._collection.count(),
            )
        except ImportError:
            logger.error("chromadb가 설치되지 않았습니다: pip install chromadb")
            return
        except Exception as exc:
            logger.error("ChromaDB 초기화 실패: %s", exc)
            return

        try:
            from sentence_transformers import SentenceTransformer

            model_name = settings.RAG_EMBED_MODEL
            self._embed_model = SentenceTransformer(model_name)
            logger.info("임베딩 모델 로드 완료: %s", model_name)
        except ImportError:
            logger.error(
                "sentence-transformers가 설치되지 않았습니다: "
                "pip install sentence-transformers"
            )
            return
        except Exception as exc:
            logger.error("임베딩 모델 로드 실패: %s", exc)
            return

        self._loaded = True

    def _embed(self, texts: list[str]) -> list[list[float]]:
        """텍스트 리스트를 임베딩 벡터로 변환한다."""
        if not self._embed_model:
            return []
        embeddings = self._embed_model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def index_reports(self, overwrite: bool = False) -> dict:
        """추출된 보고서 JSON을 ChromaDB에 색인한다."""
        if not self._loaded:
            self.load()
        if not self._collection:
            return {"error": "ChromaDB 미초기화"}

        if overwrite:
            # 기존 색인 삭제 후 재생성
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=str(CHROMA_DIR),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            client.delete_collection(COLLECTION_NAME)
            self._collection = client.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

        if not EXTRACTED_DIR.exists():
            logger.warning("추출 디렉토리 없음: %s", EXTRACTED_DIR)
            return {"total_files": 0, "total_chunks": 0}

        json_files = sorted(EXTRACTED_DIR.glob("*.json"))
        logger.info("색인 대상 파일: %d개", len(json_files))

        total_chunks = 0
        indexed_reports = []

        for json_path in json_files:
            try:
                sections = json.loads(json_path.read_text(encoding="utf-8"))
                report_chunks = 0

                for section in sections:
                    content = section.get("content", "")
                    if not content.strip():
                        continue

                    chunks = _chunk_text(content)

                    for i, chunk in enumerate(chunks):
                        doc_id = (
                            f"{section['report_id']}"
                            f"__{section['chapter']}"
                            f"__{section.get('section', 'unknown')}"
                            f"__chunk{i}"
                        )
                        # 중복 방지
                        existing = self._collection.get(ids=[doc_id])
                        if existing and existing["ids"]:
                            continue

                        embedding = self._embed([chunk])
                        if not embedding:
                            continue

                        self._collection.add(
                            ids=[doc_id],
                            embeddings=embedding,
                            documents=[chunk],
                            metadatas=[{
                                "report_id": section.get("report_id", ""),
                                "project_type": section.get("project_type", ""),
                                "project_type_code": section.get("project_type_code", ""),
                                "project_name": section.get("project_name", ""),
                                "year": section.get("year", ""),
                                "chapter": section.get("chapter", ""),
                                "section": section.get("section", ""),
                                "page_range": section.get("page_range", ""),
                            }],
                        )
                        report_chunks += 1

                total_chunks += report_chunks
                indexed_reports.append({
                    "file": json_path.name,
                    "chunks": report_chunks,
                })
                logger.info("  색인 완료: %s (%d 청크)", json_path.name, report_chunks)

            except Exception as exc:
                logger.error("색인 실패 (%s): %s", json_path.name, exc)

        logger.info("전체 색인 완료: %d개 파일, %d개 청크", len(json_files), total_chunks)
        return {
            "total_files": len(json_files),
            "total_chunks": total_chunks,
            "reports": indexed_reports,
        }

    def search(
        self,
        query: str,
        n_results: int = 5,
        project_type: str | None = None,
    ) -> list[dict]:
        """벡터 유사도 검색으로 관련 청크를 찾는다."""
        if not self._loaded:
            self.load()
        if not self._collection or self._collection.count() == 0:
            return []

        embedding = self._embed([query])
        if not embedding:
            return []

        where_filter = None
        if project_type:
            where_filter = {"project_type_code": project_type}

        try:
            results = self._collection.query(
                query_embeddings=embedding,
                n_results=min(n_results, self._collection.count()),
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            logger.error("검색 오류: %s", exc)
            return []

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                chunks.append({
                    "id": doc_id,
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i],
                    "similarity": 1 - results["distances"][0][i],
                })

        return chunks

    async def query(
        self,
        question: str,
        n_results: int = 5,
        project_type: str | None = None,
    ) -> dict[str, Any]:
        """RAG 질의: 벡터 검색 + LLM 답변 생성.

        Args:
            question: 사용자 질문
            n_results: 검색할 유사 청크 수
            project_type: 사업유형 필터 (선택)

        Returns:
            answer, sources, disclaimer 포함 딕셔너리
        """
        # 1. 벡터 검색
        chunks = self.search(question, n_results=n_results, project_type=project_type)

        if not chunks:
            return {
                "answer": "색인된 평가서가 없거나 관련 내용을 찾을 수 없습니다. "
                          "먼저 평가서를 크롤링하고 색인해 주세요.",
                "sources": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "disclaimer": _DISCLAIMER,
            }

        # 2. 컨텍스트 구성
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            source_ref = (
                f"{meta.get('project_name', '?')} "
                f"{meta.get('chapter', '')} {meta.get('section', '')} "
                f"(p.{meta.get('page_range', '?')})"
            )
            context_parts.append(f"[출처 {i}] {source_ref}\n{chunk['content']}")
            sources.append({
                "report_id": meta.get("report_id", ""),
                "project_name": meta.get("project_name", ""),
                "project_type": meta.get("project_type", ""),
                "year": meta.get("year", ""),
                "chapter": meta.get("chapter", ""),
                "section": meta.get("section", ""),
                "page_range": meta.get("page_range", ""),
                "similarity": round(chunk["similarity"], 3),
                "excerpt": chunk["content"][:200],
            })

        context = "\n\n---\n\n".join(context_parts)

        # 3. LLM 답변 생성
        answer = await self._generate_answer(question, context, sources)

        return {
            "answer": answer,
            "sources": sources,
            "total_indexed": self._collection.count() if self._collection else 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "disclaimer": _DISCLAIMER,
        }

    async def draft_assist(
        self,
        section_topic: str,
        project_type: str,
        risk_cards: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Draft Copilot 보조: 실제 평가서 문장을 참조하여 초안 작성을 지원한다.

        Args:
            section_topic: 섹션 주제 (예: "대기질", "수질", "소음")
            project_type: 사업유형 코드 (예: "road", "housing")
            risk_cards: 리스크 카드 목록 (선택)

        Returns:
            reference_text, sources 포함 딕셔너리
        """
        # 사업유형 코드→한국어 매핑 (환경영향평가법 시행령 별표3 기준 17개 유형)
        type_kr = {
            "urban_dev": "도시개발", "industrial": "산업입지",
            "energy": "에너지개발", "port": "항만건설",
            "road": "도로건설", "water_resource": "수자원개발",
            "railway": "철도건설", "airport": "공항건설",
            "river": "하천이용개발", "tourism": "관광단지개발",
            "mountain": "산지개발", "sports": "체육시설",
            "waste": "폐기물처리시설", "military": "국방군사시설",
            "mining": "토석광물채취", "reclamation": "매립간척",
            "etc": "기타",
            # 이전 호환
            "power_plant": "에너지개발", "factory": "산업입지", "housing": "도시개발",
        }.get(project_type, project_type)

        # 검색 쿼리 구성
        query = f"{type_kr} 사업 {section_topic} 현황 및 영향"
        if risk_cards:
            risk_keywords = " ".join(
                c.get("title", "") for c in risk_cards[:3]
            )
            query += f" {risk_keywords}"

        chunks = self.search(query, n_results=3, project_type=project_type)

        if not chunks:
            return {
                "available": False,
                "reference_text": "",
                "sources": [],
            }

        # 참조 텍스트 구성
        ref_parts = []
        sources = []
        for chunk in chunks:
            meta = chunk["metadata"]
            source = (
                f"(출처: {meta.get('project_name', '?')} "
                f"환경영향평가서, {meta.get('year', '?')}, "
                f"p.{meta.get('page_range', '?')})"
            )
            ref_parts.append(f"{chunk['content'][:300]}\n{source}")
            sources.append({
                "report_id": meta.get("report_id", ""),
                "project_name": meta.get("project_name", ""),
                "year": meta.get("year", ""),
                "page_range": meta.get("page_range", ""),
                "similarity": round(chunk["similarity"], 3),
            })

        reference_text = "\n\n".join(ref_parts)

        return {
            "available": True,
            "reference_text": reference_text,
            "sources": sources,
            "section_topic": section_topic,
            "project_type": type_kr,
        }

    def get_stats(self) -> dict:
        """색인 통계를 반환한다."""
        if not self._loaded:
            self.load()

        if not self._collection:
            return {
                "status": "not_initialized",
                "total_chunks": 0,
                "total_reports": 0,
                "by_project_type": {},
            }

        total = self._collection.count()

        # 사업유형별 분포 (샘플링으로 추정)
        by_type: dict[str, int] = {}
        if total > 0:
            try:
                sample = self._collection.get(
                    limit=min(total, 1000),
                    include=["metadatas"],
                )
                for meta in sample["metadatas"]:
                    ptype = meta.get("project_type", "unknown")
                    by_type[ptype] = by_type.get(ptype, 0) + 1
            except Exception:
                pass

        # 보고서 수 추정
        report_ids = set()
        if total > 0:
            try:
                sample = self._collection.get(
                    limit=min(total, 1000),
                    include=["metadatas"],
                )
                for meta in sample["metadatas"]:
                    rid = meta.get("report_id", "")
                    if rid:
                        report_ids.add(rid)
            except Exception:
                pass

        return {
            "status": "ready" if total > 0 else "empty",
            "total_chunks": total,
            "total_reports": len(report_ids),
            "by_project_type": by_type,
            "embed_model": settings.RAG_EMBED_MODEL,
            "chroma_dir": str(CHROMA_DIR),
        }

    async def _generate_answer(
        self, question: str, context: str, sources: list[dict],
    ) -> str:
        """검색된 컨텍스트를 기반으로 LLM 답변을 생성한다."""
        if not settings.OPENROUTER_API_KEY:
            return (
                "LLM API 키가 설정되지 않아 자동 답변을 생성할 수 없습니다.\n\n"
                "검색된 원문 내용을 직접 참조해 주세요."
            )

        system_prompt = (
            "당신은 대한민국 환경영향평가 전문가입니다. "
            "아래 제공된 실제 환경영향평가서 원문을 참조하여 질문에 답변하세요.\n\n"
            "답변 지침:\n"
            "- 반드시 제공된 원문 내용에 근거하여 답변하세요.\n"
            "- 각 핵심 내용 뒤에 출처를 표시하세요 (예: [출처 1]).\n"
            "- 원문에 없는 내용은 추측하지 마세요.\n"
            "- 전문적이지만 이해하기 쉬운 한국어를 사용하세요.\n"
            f"- 중요: {_DISCLAIMER}"
        )

        user_prompt = (
            f"## 질문\n{question}\n\n"
            f"## 참조할 평가서 원문\n{context}\n\n"
            "위 원문을 참조하여 질문에 답변해 주세요. "
            "각 내용의 출처를 [출처 N] 형식으로 표시해 주세요."
        )

        try:
            client = AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
            )
            response = await client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("RAG LLM 호출 실패: %s", exc)
            return f"[LLM 호출 실패] {exc}\n\n검색된 원문 내용을 직접 참조해 주세요."
