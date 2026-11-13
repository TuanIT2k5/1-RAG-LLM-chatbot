import inspect
import re
import time
from typing import Dict, List, Optional, Tuple
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConversationNotFoundException, LLMServiceException
from app.core.logging import get_logger
from app.database.models import Conversation, Message
from app.database.repositories.conversation_repo import ConversationRepository
from app.database.repositories.document_repo import DocumentRepository
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.citation_service import CitationService, resolve_citations_or_refuse
from app.services.context_builder import ContextBuilder
from app.services.llm_service import (
    MAX_CHAT_HISTORY_MESSAGES,
    NO_CONTEXT_REFUSAL_MESSAGE,
    LLMService,
    clean_robotic_phrases,
    get_llm_service,
)
from app.services.retriever import SemanticRetriever
from app.utils.text_cleaner import (
    MOJIBAKE_CHAT_REFUSAL_MESSAGE,
    is_gibberish,
    normalize_unicode_nfc,
)

logger = get_logger(__name__)

MAX_TITLE_LENGTH = 80

# Mẫu nhận diện câu hỏi nối tiếp ngắn trong hội thoại (ví dụ: "Thế làm nửa năm thì sao?", "Còn thử việc thì sao?")
_FOLLOWUP_QUESTION_PATTERN = re.compile(
    r"^\s*(?:thế\b|vậy\b|còn\b|nếu\s+vậy\b|trường\s+hợp\s+(?:này|đó)\b|ý\s+(?:này|đó|trên)\b|sao\s+nữa\b)",
    flags=re.IGNORECASE | re.UNICODE,
)


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


def _is_followup_question(question: str) -> bool:
    """Kiểm tra xem câu hỏi có phải câu hỏi nối tiếp phụ thuộc ngữ cảnh câu trước hay không."""
    cleaned = normalize_unicode_nfc(question or "").strip()
    if not cleaned:
        return False
    word_count = len(cleaned.split())
    if _FOLLOWUP_QUESTION_PATTERN.search(cleaned) and word_count <= 10:
        return True
    return word_count <= 5


def _build_natural_extractive_answer(
    question: str,
    source_map: Dict[str, object],
) -> str:
    """
    Tổng hợp câu trả lời tự nhiên, thân thiện (xưng 'tôi' - gọi 'bạn', không dùng câu mở đầu máy móc)
    khi chạy ở chế độ dự phòng cục bộ chưa có LLM_API_KEY hợp lệ.
    """
    entries = list(source_map.values())
    if not entries:
        return NO_CONTEXT_REFUSAL_MESSAGE

    top_items = list(source_map.items())[:3]
    if len(top_items) == 1:
        sid, entry = top_items[0]
        excerpt = getattr(entry, "excerpt", "").strip()
        return (
            f"Chào bạn, về vấn đề bạn hỏi thì tôi xin chia sẻ thông tin cụ thể như sau nhé:\n\n"
            f"{excerpt} [{sid}]\n\n"
            f"Bạn nhấn vào thẻ [{sid}] để xem trực tiếp đoạn này trong tài liệu nhé!"
        )

    lines = [
        "Chào bạn, tôi tổng hợp nhanh các thông tin bạn cần như sau nhé:"
    ]
    for sid, entry in top_items:
        excerpt = getattr(entry, "excerpt", "").strip()
        lines.append(f"- {excerpt} [{sid}]")
    lines.append(
        "Bạn có thể nhấn vào các thẻ trích dẫn ở trên để đối chiếu trực tiếp trang tài liệu gốc nhé!"
    )
    return "\n\n".join(lines)


class RAGPipeline:
    """
    [SP4-05.1 -> SP4-05.4 & 5 Bước Trả lời Tự nhiên] Bộ điều phối trung tâm luồng Hỏi - Đáp RAG khép kín:
    1. Quản lý phiên hội thoại (tự tạo mới nếu chưa có conversation_id).
    2. Truy vấn 3-5 tin nhắn lịch sử gần nhất từ Database để duy trì mạch hội thoại ([Bước 2]).
    3. Lưu tin nhắn câu hỏi của người dùng ('user') vào bảng 'messages'.
    4. Truy xuất Top-K đoạn văn bản ngữ nghĩa từ ChromaDB (có lọc document_ids và hỗ trợ câu hỏi nối tiếp).
    5. Đóng gói ngữ cảnh [S1], [S2]... và tạo bảng ánh xạ source_map.
    6. Gọi LLM với System Prompt thân thiện, Few-Shot Prompting, Temperature 0.5 và lịch sử hội thoại.
    7. Lọc bỏ các cụm từ rập khuôn ([Bước 5]) và xác thực trích dẫn hai lớp (Regex + đối chiếu source_map).
    8. Lưu tin nhắn trả lời ('assistant') vào bảng 'messages' và nguồn vào 'message_sources'.
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
        [SP4-05.1 -> SP4-05.3 & Bước 2] Thực thi toàn bộ luồng hỏi đáp RAG tự nhiên kèm lịch sử hội thoại.
        """
        pipeline_start = time.perf_counter()
        cleaned_question = normalize_unicode_nfc(request.question).strip()

        # Bước 1: [SP4-05.2] Lấy phiên hội thoại hiện tại hoặc tự động tạo mới theo câu hỏi đầu tiên
        chat_history: List[Dict[str, str]] = []
        if request.conversation_id is not None:
            conversation = self.conversation_repo.get_conversation_by_id(
                request.conversation_id
            )
            if conversation is None:
                raise ConversationNotFoundException(
                    conversation_id=str(request.conversation_id)
                )
            # [Bước 2] Truy vấn Database lấy 3-5 tin nhắn gần nhất của phiên hội thoại để gửi kèm cho AI
            previous_messages = self.conversation_repo.get_messages_by_conversation(
                conversation.id
            )
            for msg in previous_messages[-MAX_CHAT_HISTORY_MESSAGES:]:
                if msg.content and msg.content.strip() != NO_CONTEXT_REFUSAL_MESSAGE:
                    chat_history.append(
                        {
                            "role": msg.role,
                            "content": msg.content.strip(),
                        }
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
        # [Bước 2] Nếu người dùng hỏi câu nối tiếp ngắn (ví dụ: "Thế làm nửa năm thì sao?")
        # và truy vấn đơn lẻ chưa khớp hoặc cần bổ sung ngữ cảnh từ câu hỏi liền trước:
        if chat_history and _is_followup_question(cleaned_question):
            last_user_turns = [
                turn["content"] for turn in chat_history if turn["role"] == "user"
            ]
            if last_user_turns:
                contextualized_query = f"{last_user_turns[-1]} {cleaned_question}"
                expanded_chunks = self.retriever.retrieve(
                    question=contextualized_query,
                    top_k=request.top_k,
                    document_ids=request.document_ids,
                )
                if not retrieved_chunks and expanded_chunks:
                    retrieved_chunks = expanded_chunks
                elif expanded_chunks:
                    seen_ids = {c.chunk_id for c in retrieved_chunks}
                    for ch in expanded_chunks:
                        if ch.chunk_id not in seen_ids and len(retrieved_chunks) < (request.top_k or 5):
                            retrieved_chunks.append(ch)
                            seen_ids.add(ch.chunk_id)

        retrieve_ms = (time.perf_counter() - t_ret) * 1000.0

        # [Phần 2 - Bước 4] Kiểm tra nếu các đoạn văn truy xuất được (từ tài liệu cũ) bị lỗi mã hóa chữ (Mojibake)
        had_raw_chunks = len(retrieved_chunks) > 0
        valid_chunks = [c for c in retrieved_chunks if not is_gibberish(c.text)]
        if had_raw_chunks and not valid_chunks:
            from app.services.citation_service import VerifiedCitationResult

            verified_result = VerifiedCitationResult(
                answer=MOJIBAKE_CHAT_REFUSAL_MESSAGE,
                sources=[],
                valid_source_ids=[],
                removed_source_ids=[],
                skipped_llm=True,
            )
            llm_ms = 0.0
        else:
            retrieved_chunks = valid_chunks
            # Bước 4: [SP4-03.4] Kiểm tra trường hợp không tìm thấy ngữ cảnh phù hợp
            fast_refusal = resolve_citations_or_refuse(retrieved_chunks)
            if fast_refusal is not None:
                verified_result = fast_refusal
                llm_ms = 0.0
            else:
                # Đóng gói Context [S1], [S2]... và tạo bảng source_map ([SP4-01])
                built_ctx = self.context_builder.build(retrieved_chunks)

                # Gọi LLM sinh câu trả lời tự nhiên kèm lịch sử hội thoại ([SP4-02 & Bước 1-4])
                t_llm = time.perf_counter()
                try:
                    sig = inspect.signature(self.llm_service.generate_answer)
                    if "chat_history" in sig.parameters:
                        raw_answer = self.llm_service.generate_answer(
                            question=cleaned_question,
                            context_text=built_ctx.context_text,
                            chat_history=chat_history,
                        )
                    else:
                        raw_answer = self.llm_service.generate_answer(
                            question=cleaned_question,
                            context_text=built_ctx.context_text,
                        )
                except LLMServiceException as exc:
                    details_str = str(exc.details)
                    if "API_KEY_INVALID" in details_str or "API key not valid" in details_str:
                        logger.warning(
                            "LLM_API_KEY chưa hợp lệ với Google AI Studio; tự động tổng hợp câu trả lời tự nhiên từ Top-K."
                        )
                        raw_answer = _build_natural_extractive_answer(
                            question=cleaned_question,
                            source_map=built_ctx.source_map,
                        )
                    else:
                        raise
                llm_ms = (time.perf_counter() - t_llm) * 1000.0

                # [Bước 5 & SP4-03] Lọc bỏ câu mở đầu rập khuôn và xác thực trích dẫn hai lớp
                cleaned_raw_answer = clean_robotic_phrases(raw_answer)
                verified_result = self.citation_service.verify_and_map(
                    answer_text=cleaned_raw_answer,
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
            "Hoàn tất RAG Chat (conv_id=%s, history=%d, sources=%d, skipped_llm=%s) | "
            "retrieve=%.1fms, llm=%.1fms, total=%.1fms",
            conversation.id,
            len(chat_history),
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
