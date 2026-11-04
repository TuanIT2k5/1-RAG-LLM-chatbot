from fastapi import Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.document_service import DocumentService
from app.services.rag_pipeline import RAGPipeline


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    """Dependency Injection khởi tạo DocumentService gắn với phiên làm việc PostgreSQL hiện tại."""
    return DocumentService(db=db)


def get_rag_pipeline(db: Session = Depends(get_db)) -> RAGPipeline:
    """Dependency Injection khởi tạo RAGPipeline gắn với phiên làm việc PostgreSQL hiện tại."""
    return RAGPipeline(db=db)


__all__ = ["get_db", "get_document_service", "get_rag_pipeline"]
