import re
import time
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConversationNotFoundException
from app.core.logging import get_logger
from app.database.models import Conversation, Message
from app.database.repositories.conversation_repo import ConversationRepository
from app.database.repositories.document_repo import DocumentRepository
from app.schemas.chat_schema import ChatRequest, ChatResponse, SourceCitation
from app.services.citation_service import CitationService, resolve_citations_or_refuse
from app.services.context_builder import ContextBuilder
from app.services.llm_service import LLMService, get_llm_service
from app.services.retriever import SemanticRetriever
from app.utils.text_cleaner import normalize_unicode_nfc

logger = get_logger(__name__)

MAX_TITLE_LENGTH = 80


def generate_conversation_title(
    first_question: str,
    max_length: int = MAX_TITLE_LENGTH,
) -> str:
    """
    [SP4-05.2] Tự động tạo tiêu đề phiên hội thoại gọn gàng dựa trên câu hỏi đầu tiên của người dùng.
    """
    cleaned = normalize_unicode_nfc(first_question or "").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return "Cuộc trò chuyện mới"
    if len(cleaned) <= max_length:
        return cleaned
    truncated = cleaned[: max_length - 3].rsplit(" ", 1)[0].strip()
    return f"{truncated or cleaned[: max_length - 3]}..."


class RAGPipeline:
    """
    [SP4-05.1 -> SP4-05.4] Bộ điều phối trung tâm luồng Hỏi - Đáp RAG khép kín:
    1. Quản lý phiên hội thoại (tự tạo mới nếu chưa có conversation_id).
    2. Lưu tin nhắn câu hỏi của người dùng ('user') vào bảng 'messages'.
    3. Truy xuất Top-K đoạn văn bản ngữ nghĩa từ ChromaDB (có lọc document_ids).
    4. Đóng gói ngữ cảnh [S1], [S2]... và tạo bảng ánh xạ source_map.
    5. Gọi LLM sinh câu trả lời an toàn (hoặc từ chối ngay nếu không có ngữ cảnh).
    6. Xác thực trích dẫn hai lớp (Regex + đối chiếu source_map).
    7. Lưu tin nhắn trả lời ('assistant') vào bảng 'messages' và nguồn vào 'message_sources'.
    """

    def __init__(
        self,
        db: Session,
        retriever: Optional[SemanticRetriever] = None,
        context_builder: Optional[ContextBuilder] = None,
        llm_service: Optional[LLMService] = None,
        citation_service: Optional[CitationService] = None,
    ) -> None:
        self.db = db
        self.conversation_repo = ConversationRepository(db)
        self.document_repo = DocumentRepository(db)
        self.retriever = retriever or SemanticRetriever()
        self.context_builder = context_builder or ContextBuilder()
        self.llm_service = llm_service or get_llm_service()
        self.citation_service = citation_service or CitationService()

    def ask(
        self,
        request: ChatRequest,
        user_id: Optional[uuid.UUID] = None,
    ) -> ChatResponse:
        """
        [SP4-05.1 -> SP4-05.3] Thực thi toàn bộ luồng hỏi đáp RAG và lưu trữ lịch sử SQL.
        """
        pipeline_start = time.perf_counter()
        cleaned_question = normalize_unicode_nfc(request.question).strip()

        # Bước 1: [SP4-05.2] Lấy phiên hội thoại hiện tại hoặc tự động tạo mới theo câu hỏi đầu tiên
        if request.conversation_id is not None:
            conversation = self.conversation_repo.get_conversation_by_id(
                request.conversation_id
            )
            if conversation is None:
                raise ConversationNotFoundException(
                    conversation_id=str(request.conversation_id)
                )
        else:
            title = generate_conversation_title(cleaned_question)
            conversation = self.conversation_repo.create_conversation(
                title=title,
                user_id=user_id,
            )

        # Bước 2: [SP4-05.3] Lưu câu hỏi của người dùng vào bảng 'messages'
        self.conversation_repo.add_message(
            conversation_id=conversation.id,
            role="user",
            content=cleaned_question,
        )

        # Bước 3: Truy xuất ngữ nghĩa Top-K đoạn văn từ ChromaDB
        t_ret = time.perf_counter()
        retrieved_chunks = self.retriever.retrieve(
            question=cleaned_question,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        retrieve_ms = (time.perf_counter() - t_ret) * 1000.0

        # Bước 4: [SP4-03.4] Kiểm tra trường hợp không tìm thấy ngữ cảnh phù hợp
        fast_refusal = resolve_citations_or_refuse(retrieved_chunks)
        if fast_refusal is not None:
            verified_result = fast_refusal
            llm_ms = 0.0
        else:
            # Đóng gói Context [S1], [S2]... và tạo bảng source_map ([SP4-01])
            built_ctx = self.context_builder.build(retrieved_chunks)

            # Gọi LLM sinh câu trả lời ([SP4-02])
            t_llm = time.perf_counter()
            raw_answer = self.llm_service.generate_answer(
                question=cleaned_question,
                context_text=built_ctx.context_text,
            )
            llm_ms = (time.perf_counter() - t_llm) * 1000.0

            # Xác thực trích dẫn hai lớp ([SP4-03])
            verified_result = self.citation_service.verify_and_map(
                answer_text=raw_answer,
                source_map=built_ctx.source_map,
            )

        # Bước 5: [SP4-05.3] Lưu câu trả lời của AI vào bảng 'messages' và nguồn vào 'message_sources'
        assistant_msg = self.conversation_repo.add_message(
            conversation_id=conversation.id,
            role="assistant",
            content=verified_result.answer,
            citations=verified_result.sources,
        )

        total_ms = (time.perf_counter() - pipeline_start) * 1000.0
        logger.info(
            "Hoàn tất RAG Chat (conv_id=%s, sources=%d, skipped_llm=%s) | "
            "retrieve=%.1fms, llm=%.1fms, total=%.1fms",
            conversation.id,
            len(verified_result.sources),
            verified_result.skipped_llm,
            retrieve_ms,
            llm_ms,
            total_ms,
        )

        return ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_msg.id,
            question=cleaned_question,
            answer=verified_result.answer,
            sources=verified_result.sources,
            created_at=assistant_msg.created_at,
        )

    def list_conversations(
        self,
        user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[int, List[Conversation]]:
        """[SP4-05.4] Lấy tổng số và danh sách các phiên hội thoại đã lưu."""
        total = self.conversation_repo.count_conversations(user_id=user_id)
        items = self.conversation_repo.list_conversations(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )
        return total, items

    def get_conversation_history(
        self,
        conversation_id: uuid.UUID,
    ) -> Tuple[Conversation, List[Message]]:
        """
        [SP4-05.4] Lấy thông tin phiên hội thoại và toàn bộ lịch sử tin nhắn kèm nguồn trích dẫn.
        Ném lỗi 404 (CONVERSATION_NOT_FOUND) nếu phiên hội thoại không tồn tại.
        """
        conv = self.conversation_repo.get_conversation_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundException(conversation_id=str(conversation_id))
        messages = self.conversation_repo.get_messages_by_conversation(conversation_id)
        return conv, messages

    def delete_conversation(self, conversation_id: uuid.UUID) -> bool:
        """Xóa một phiên hội thoại và toàn bộ tin nhắn liên quan."""
        conv = self.conversation_repo.get_conversation_by_id(conversation_id)
        if conv is None:
            raise ConversationNotFoundException(conversation_id=str(conversation_id))
        return self.conversation_repo.delete_conversation(conversation_id)

