import threading
import time
from typing import Any, List, Optional, Sequence

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.text_cleaner import normalize_unicode_nfc

logger = get_logger(__name__)


def detect_compute_device(preferred_device: Optional[str] = None) -> str:
    """
    [SP3-01.2] Tự động nhận diện thiết bị phần cứng (CUDA GPU nếu có, MPS hoặc CPU)
    để tối ưu tốc độ tính toán vector embedding.
    """
    if preferred_device and preferred_device.strip():
        return preferred_device.strip().lower()

    try:
        import torch  # type: ignore[import-not-found]

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info("Phát hiện GPU CUDA khả dụng: %s", gpu_name)
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            logger.info("Phát hiện Apple MPS GPU khả dụng.")
            return "mps"
    except Exception:
        pass

    return "cpu"


def _l2_normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    """Chuẩn hóa L2 từng hàng vector để độ dài Euclidean bằng 1.0 (tối ưu cho khoảng cách Cosine)."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0, 1.0, norms)
    return matrix / safe_norms


class EmbeddingService:
    """
    [SP3-01.1 -> SP3-01.4] Dịch vụ sinh vector đa ngôn ngữ (BAAI/bge-m3) thiết kế theo
    mẫu Singleton (Thread-safe), đảm bảo mô hình chỉ được nạp vào bộ nhớ duy nhất một lần.
    """

    _instance: Optional["EmbeddingService"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "EmbeddingService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        model_name: Optional[str] = None,
        device: Optional[str] = None,
        default_batch_size: int = 32,
        custom_model: Optional[Any] = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            # Nếu truyền custom_model (ví dụ trong môi trường test), cho phép cập nhật
            if custom_model is not None:
                self._model = custom_model
            return

        self.model_name: str = (
            model_name
            or settings.EMBEDDING_MODEL_NAME
            or settings.EMBEDDING_MODEL
            or "BAAI/bge-m3"
        )
        self.device: str = detect_compute_device(device)
        self.default_batch_size: int = max(1, default_batch_size)
        self._model: Optional[Any] = custom_model
        self._model_lock: threading.Lock = threading.Lock()
        self._initialized: bool = True

        logger.info(
            "Khởi tạo EmbeddingService Singleton (model='%s', device='%s', batch_size=%d)",
            self.model_name,
            self.device,
            self.default_batch_size,
        )

    @property
    def model(self) -> Any:
        """Tải mô hình SentenceTransformer vào bộ nhớ ở lần gọi đầu tiên và giữ cố định."""
        if self._model is None:
            with self._model_lock:
                if self._model is None:
                    self._load_sentence_transformer()
        return self._model

    def _load_sentence_transformer(self) -> None:
        """Nạp mô hình BAAI/bge-m3 qua thư viện sentence-transformers."""
        start_time = time.perf_counter()
        logger.info(
            "Đang nạp mô hình Embedding '%s' trên thiết bị '%s'...",
            self.model_name,
            self.device,
        )
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        self._model = SentenceTransformer(self.model_name, device=self.device)
        elapsed = time.perf_counter() - start_time
        logger.info(
            "Hoàn tất nạp mô hình '%s' trên '%s' trong %.2f giây.",
            self.model_name,
            self.device,
            elapsed,
        )

    def set_model(self, model_obj: Any) -> None:
        """Gán mô hình tùy chỉnh (hữu ích khi kiểm thử đơn vị hoặc thay thế backend)."""
        with self._model_lock:
            self._model = model_obj

    def encode_documents(
        self,
        texts: Sequence[str],
        batch_size: Optional[int] = None,
        normalize_embeddings: bool = True,
    ) -> List[List[float]]:
        """
        [SP3-01.3] Chuyển đổi danh sách các đoạn văn bản (Chunks) thành mảng vector
        xử lý theo từng lô (batch_size) với cờ normalize_embeddings=True.
        """
        if not texts:
            return []

        cleaned_texts: List[str] = []
        for idx, raw_text in enumerate(texts):
            normalized = normalize_unicode_nfc(raw_text or "").strip()
            if not normalized:
                raise ValueError(
                    f"Văn bản tại vị trí index={idx} bị rỗng, không thể tạo vector embedding."
                )
            cleaned_texts.append(normalized)

        effective_batch_size = (
            batch_size if batch_size and batch_size > 0 else self.default_batch_size
        )
        start_time = time.perf_counter()

        raw_vectors = self.model.encode(
            cleaned_texts,
            batch_size=effective_batch_size,
            normalize_embeddings=normalize_embeddings,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

        matrix = np.asarray(raw_vectors, dtype=np.float32)
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)

        if normalize_embeddings:
            matrix = _l2_normalize_matrix(matrix)

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Đã sinh %d vector tài liệu (dim=%d, batch_size=%d) trong %.3f giây.",
            matrix.shape[0],
            matrix.shape[1],
            effective_batch_size,
            elapsed,
        )
        return matrix.tolist()

    def encode_query(
        self,
        query: str,
        normalize_embeddings: bool = True,
    ) -> List[float]:
        """
        [SP3-01.4] Vector hóa câu hỏi của người dùng trên cùng mô hình và không gian
        chuẩn hóa với tài liệu để tính độ tương đồng Cosine chính xác.
        """
        cleaned_query = normalize_unicode_nfc(query or "").strip()
        if not cleaned_query:
            raise ValueError("Câu hỏi truy vấn (query) không được để trống.")

        vectors = self.encode_documents(
            [cleaned_query],
            batch_size=1,
            normalize_embeddings=normalize_embeddings,
        )
        return vectors[0]


def get_embedding_service() -> EmbeddingService:
    """Trả về thực thể EmbeddingService Singleton toàn cục."""
    return EmbeddingService()

