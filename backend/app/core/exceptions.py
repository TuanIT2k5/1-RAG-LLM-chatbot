from typing import Any, Dict, Optional


class AppException(Exception):
    """Ngoại lệ cơ sở chuẩn hóa cho toàn bộ ứng dụng Backend."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidFileException(AppException):
    """Lỗi định dạng tệp tải lên không hợp lệ (chỉ chấp nhận PDF và DOCX)."""

    def __init__(
        self,
        message: str = "Định dạng tệp không hợp lệ. Hệ thống chỉ hỗ trợ tệp .pdf và .docx.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            error_code="INVALID_FILE",
            message=message,
            status_code=400,
            details=details,
        )


class FileTooLargeException(AppException):
    """Lỗi tệp tải lên vượt quá dung lượng cho phép."""

    def __init__(
        self,
        max_size_mb: int = 20,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            error_code="FILE_TOO_LARGE",
            message=f"Dung lượng tệp vượt quá giới hạn tối đa cho phép ({max_size_mb}MB).",
            status_code=413,
            details=details,
        )


class EmptyDocumentException(AppException):
    """Lỗi tài liệu rỗng hoặc tệp PDF chỉ chứa ảnh quét không có lớp văn bản."""

    def __init__(
        self,
        message: str = "Không trích xuất được văn bản từ tài liệu (tệp rỗng hoặc PDF dạng ảnh scan chưa có OCR).",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            error_code="EMPTY_DOCUMENT",
            message=message,
            status_code=422,
            details=details,
        )


class DocumentNotFoundException(AppException):
    """Lỗi không tìm thấy tài liệu theo ID."""

    def __init__(
        self,
        document_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            error_code="DOCUMENT_NOT_FOUND",
            message=f"Không tìm thấy tài liệu với mã định danh '{document_id}'.",
            status_code=404,
            details=details,
        )


class LLMServiceException(AppException):
    """Lỗi kết nối hoặc quá thời gian chờ từ dịch vụ LLM."""

    def __init__(
        self,
        message: str = "Dịch vụ AI hiện đang phản hồi chậm hoặc gián đoạn. Vui lòng thử lại sau giây lát.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            error_code="LLM_SERVICE_ERROR",
            message=message,
            status_code=503,
            details=details,
        )

