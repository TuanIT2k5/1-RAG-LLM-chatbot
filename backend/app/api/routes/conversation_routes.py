import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_rag_pipeline
from app.schemas.conversation_schema import (
    ConversationHistoryResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageResponse,
)
from app.services.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/conversations", tags=["Conversations & History"])


@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy danh sách các phiên hội thoại đã lưu",
)
def list_conversations(
    skip: int = Query(default=0, ge=0, description="Số bản ghi bỏ qua (phân trang)"),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Số lượng phiên hội thoại tối đa trả về",
    ),
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ConversationListResponse:
    """
    [SP4-05.4] Trả về danh sách các phiên hội thoại đã lưu sắp xếp từ mới nhất đến cũ nhất.
    """
    total, items = rag_pipeline.list_conversations(skip=skip, limit=limit)
    return ConversationListResponse(
        total=total,
        items=[ConversationResponse.model_validate(c) for c in items],
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=ConversationHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Lấy toàn bộ lịch sử tin nhắn và trích dẫn đi kèm của một phiên hội thoại",
)
def get_conversation_messages(
    conversation_id: uuid.UUID,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ConversationHistoryResponse:
    """
    [SP4-05.4] Tải lại toàn bộ lịch sử tin nhắn ('user' và 'assistant') cùng danh sách
    nguồn trích dẫn xác thực ('sources') của một phiên hội thoại theo ID.
    """
    conv, messages = rag_pipeline.get_conversation_history(conversation_id)
    return ConversationHistoryResponse(
        conversation=ConversationResponse.model_validate(conv),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa một phiên hội thoại và toàn bộ lịch sử tin nhắn liên quan",
)
def delete_conversation(
    conversation_id: uuid.UUID,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> dict:
    """Xóa phiên hội thoại và cascade xóa toàn bộ tin nhắn + trích dẫn thuộc phiên đó."""
    rag_pipeline.delete_conversation(conversation_id)
    return {
        "message": "Đã xóa phiên hội thoại thành công.",
        "conversation_id": str(conversation_id),
    }

