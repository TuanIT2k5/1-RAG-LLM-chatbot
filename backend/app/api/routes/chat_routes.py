from fastapi import APIRouter, Depends, status

from app.api.deps import get_rag_pipeline
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Hỏi đáp RAG trên tài liệu và trả về câu trả lời kèm trích dẫn hai lớp [S1], [S2]",
)
def chat_with_documents(
    request: ChatRequest,
    rag_pipeline: RAGPipeline = Depends(get_rag_pipeline),
) -> ChatResponse:
    """
    [SP4-05.1 -> SP4-05.3] Thực thi luồng hỏi đáp RAG khép kín:
    - Nhận câu hỏi (question), danh sách document_ids và conversation_id.
    - Nếu chưa truyền conversation_id, tự động tạo phiên hội thoại mới đặt tiêu đề theo câu hỏi đầu tiên.
    - Truy xuất Top-K đoạn văn ngữ nghĩa -> Đóng gói Context [S1]..[Sn] -> Gọi LLM -> Xác thực trích dẫn hai lớp.
    - Lưu câu hỏi của người dùng, câu trả lời của AI vào bảng 'messages' và các nguồn vào bảng 'message_sources'.
    """
    return rag_pipeline.ask(request)

