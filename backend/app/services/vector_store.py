from pathlib import Path
import threading
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from app.core.config import BACKEND_DIR, settings
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_COLLECTION_NAME = "documents_index"

# Kiểu dữ liệu metadata hợp lệ theo quy tắc của ChromaDB
ChromaMetadataValue = Union[str, int, float, bool]

# Giá trị mặc định thay thế cho None theo từng khóa metadata ([SP3-02.4])
INTEGER_METADATA_KEYS = {"page_number", "paragraph_index", "chunk_index", "token_count"}
MISSING_INTEGER_VALUE = -1


def resolve_chroma_persist_dir(custom_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    [SP3-02.1] Trả về đường dẫn tuyệt đối thư mục lưu trữ bền vững của ChromaDB
    (mặc định './storage/chroma_db' tính từ thư mục backend).
    """
    raw_path = Path(custom_dir) if custom_dir is not None else Path(settings.CHROMA_PERSIST_DIR)
    target = raw_path if raw_path.is_absolute() else (BACKEND_DIR / raw_path)
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    return target


def sanitize_metadata(metadata: Mapping[str, Any]) -> Dict[str, ChromaMetadataValue]:
    """
    [SP3-02.4] Chuẩn hóa kiểu dữ liệu metadata theo quy tắc của ChromaDB
    (chỉ chấp nhận str, int, float, bool; không chấp nhận None, list, dict):
    - None ở các khóa số nguyên (page_number, paragraph_index...) -> -1
    - None ở các khóa còn lại -> chuỗi rỗng ""
    - UUID / Path / kiểu khác -> chuyển thành chuỗi str
    - list / tuple / dict -> nối thành chuỗi phân tách bằng dấu phẩy
    """
    cleaned: Dict[str, ChromaMetadataValue] = {}
    for key, value in metadata.items():
        str_key = str(key)

        if value is None:
            cleaned[str_key] = (
                MISSING_INTEGER_VALUE if str_key in INTEGER_METADATA_KEYS else ""
            )
        elif isinstance(value, bool):
            cleaned[str_key] = value
        elif isinstance(value, int):
            cleaned[str_key] = int(value)
        elif isinstance(value, float):
            cleaned[str_key] = float(value)
        elif isinstance(value, str):
            cleaned[str_key] = value
        elif isinstance(value, (list, tuple, set)):
            cleaned[str_key] = ", ".join(str(item) for item in value)
        elif isinstance(value, dict):
            cleaned[str_key] = ", ".join(f"{k}={v}" for k, v in value.items())
        else:
            cleaned[str_key] = str(value)

        # Ép kiểu số nguyên cho các khóa vị trí nếu dữ liệu đến dưới dạng chuỗi số
        if str_key in INTEGER_METADATA_KEYS and isinstance(cleaned[str_key], str):
            raw_str = str(cleaned[str_key]).strip()
            cleaned[str_key] = (
                int(raw_str) if raw_str.lstrip("-").isdigit() else MISSING_INTEGER_VALUE
            )

    return cleaned


def restore_metadata(metadata: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Khôi phục giá trị None cho các trường đã được chuẩn hóa khi đọc dữ liệu từ ChromaDB."""
    if not metadata:
        return {}
    restored: Dict[str, Any] = {}
    for key, value in metadata.items():
        if key in INTEGER_METADATA_KEYS and value == MISSING_INTEGER_VALUE:
            restored[key] = None
        elif value == "":
            restored[key] = None
        else:
            restored[key] = value
    return restored


class VectorStore:
    """
    [SP3-02.1 -> SP3-02.4] Lớp giao tiếp ChromaDB PersistentClient lưu trữ bền vững
    các vector Chunk tài liệu trên ổ cứng trong Collection 'documents_index' (Cosine).
    """

    def __init__(
        self,
        persist_dir: Optional[Union[str, Path]] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        client: Optional[Any] = None,
    ) -> None:
        self.collection_name = collection_name
        self.persist_dir: Optional[Path] = None

        if client is not None:
            self.client = client
        else:
            import chromadb  # type: ignore[import-not-found]
            from chromadb.config import Settings as ChromaSettings  # type: ignore[import-not-found]

            # [SP3-02.1] Khởi tạo PersistentClient trỏ tới thư mục lưu trữ bền vững
            self.persist_dir = resolve_chroma_persist_dir(persist_dir)
            self.client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
            )

        # [SP3-02.2] Tạo hoặc lấy Collection với không gian khoảng cách Cosine
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        logger.info(
            "Khởi tạo ChromaDB VectorStore thành công (collection='%s', space=cosine, path='%s', count=%d)",
            self.collection_name,
            self.persist_dir,
            self.collection.count(),
        )

    @property
    def distance_space(self) -> str:
        """Trả về không gian đo lường khoảng cách của Collection (mặc định 'cosine')."""
        collection_meta = self.collection.metadata or {}
        return str(collection_meta.get("hnsw:space", "l2"))

    def count(self) -> int:
        """Trả về tổng số Chunk vector hiện đang lưu trong Collection."""
        return int(self.collection.count())

    def add_chunks(
        self,
        texts: Sequence[str],
        embeddings: Sequence[Sequence[float]],
        metadatas: Sequence[Mapping[str, Any]],
        chunk_ids: Sequence[str],
        batch_size: int = 256,
    ) -> int:
        """
        [SP3-02.3] Lưu danh sách văn bản, mảng vector, metadata và chunk_id vào ChromaDB.
        Sử dụng upsert để đảm bảo idempotent khi nạp lại cùng một tài liệu.
        Trả về số lượng Chunk đã được lưu.
        """
        total = len(texts)
        if total == 0:
            return 0

        if not (len(embeddings) == len(metadatas) == len(chunk_ids) == total):
            raise ValueError(
                "Số lượng texts, embeddings, metadatas và chunk_ids phải bằng nhau "
                f"(texts={total}, embeddings={len(embeddings)}, "
                f"metadatas={len(metadatas)}, chunk_ids={len(chunk_ids)})."
            )

        if len(set(chunk_ids)) != total:
            raise ValueError("Danh sách chunk_ids chứa mã định danh bị trùng lặp.")

        expected_dim = len(embeddings[0])
        for idx, vector in enumerate(embeddings):
            if len(vector) != expected_dim:
                raise ValueError(
                    f"Vector tại vị trí {idx} có số chiều {len(vector)} khác {expected_dim}."
                )

        clean_ids = [str(cid) for cid in chunk_ids]
        clean_docs = [str(text) for text in texts]
        clean_vectors = [[float(x) for x in vec] for vec in embeddings]
        clean_metas = [sanitize_metadata(meta) for meta in metadatas]

        step = max(1, batch_size)
        for start in range(0, total, step):
            end = start + step
            self.collection.upsert(
                ids=clean_ids[start:end],
                documents=clean_docs[start:end],
                embeddings=clean_vectors[start:end],
                metadatas=clean_metas[start:end],
            )

        logger.info(
            "Đã lưu %d Chunks (dim=%d) vào ChromaDB collection '%s'.",
            total,
            expected_dim,
            self.collection_name,
        )
        return total

    def get_chunks_by_ids(self, chunk_ids: Sequence[str]) -> List[Dict[str, Any]]:
        """Lấy nội dung và metadata của các Chunk theo danh sách chunk_id."""
        if not chunk_ids:
            return []
        result = self.collection.get(
            ids=[str(cid) for cid in chunk_ids],
            include=["documents", "metadatas"],
        )
        items: List[Dict[str, Any]] = []
        for cid, doc, meta in zip(
            result.get("ids", []) or [],
            result.get("documents", []) or [],
            result.get("metadatas", []) or [],
        ):
            items.append({"chunk_id": cid, "text": doc, "metadata": restore_metadata(meta)})
        return items

    def reset_collection(self) -> None:
        """Xóa toàn bộ dữ liệu và tạo lại Collection rỗng (chỉ dùng cho kiểm thử/bảo trì)."""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
            embedding_function=None,
        )
        logger.warning("Đã reset toàn bộ ChromaDB collection '%s'.", self.collection_name)


_vector_store_instance: Optional[VectorStore] = None
_vector_store_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    """Trả về thực thể VectorStore dùng chung toàn ứng dụng (khởi tạo lười một lần)."""
    global _vector_store_instance
    if _vector_store_instance is None:
        with _vector_store_lock:
            if _vector_store_instance is None:
                _vector_store_instance = VectorStore()
    return _vector_store_instance

