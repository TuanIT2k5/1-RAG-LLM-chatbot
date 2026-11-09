"""
Kiểm thử tự động xác nhận bộ cấu hình Docker & Docker Compose (SP6-04: SP6-04.1 -> SP6-04.4).
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_DOCKERFILE = PROJECT_ROOT / "backend" / "Dockerfile"
BACKEND_DOCKERIGNORE = PROJECT_ROOT / "backend" / ".dockerignore"
FRONTEND_DOCKERFILE = PROJECT_ROOT / "frontend" / "Dockerfile"
FRONTEND_DOCKERIGNORE = PROJECT_ROOT / "frontend" / ".dockerignore"
FRONTEND_NGINX_CONF = PROJECT_ROOT / "frontend" / "nginx.conf"
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.yml"


def test_sp6_04_1_backend_dockerfile_optimization_and_bge_m3_cache() -> None:
    """[SP6-04.1] Xác nhận Dockerfile Backend dùng python:3.11-slim, tách layer cache và cấu hình BGE-M3."""
    assert BACKEND_DOCKERFILE.exists(), "Thiếu backend/Dockerfile"
    assert BACKEND_DOCKERIGNORE.exists(), "Thiếu backend/.dockerignore"

    content = BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM python:3.11-slim" in content
    assert "HF_HOME=/app/storage/model_cache" in content
    assert "SENTENCE_TRANSFORMERS_HOME=/app/storage/model_cache" in content

    # Đảm bảo COPY requirements.txt đứng trước COPY app để tối ưu Docker Layer Caching
    req_pos = content.find("COPY requirements.txt")
    app_pos = content.find("COPY app ./app")
    assert req_pos != -1 and app_pos != -1 and req_pos < app_pos

    assert "EXPOSE 8000" in content
    assert "HEALTHCHECK" in content
    assert '"uvicorn", "app.main:app"' in content


def test_sp6_04_2_frontend_multistage_dockerfile_and_nginx_reverse_proxy() -> None:
    """[SP6-04.2] Xác nhận Dockerfile Frontend multi-stage (Node.js + Nginx) và cấu hình Nginx."""
    assert FRONTEND_DOCKERFILE.exists(), "Thiếu frontend/Dockerfile"
    assert FRONTEND_DOCKERIGNORE.exists(), "Thiếu frontend/.dockerignore"
    assert FRONTEND_NGINX_CONF.exists(), "Thiếu frontend/nginx.conf"

    dockerfile_text = FRONTEND_DOCKERFILE.read_text(encoding="utf-8")
    assert "FROM node:20-alpine AS builder" in dockerfile_text
    assert "FROM nginx:1.27-alpine AS production" in dockerfile_text
    assert "RUN npm ci" in dockerfile_text
    assert "RUN npm run build" in dockerfile_text
    assert "COPY --from=builder /app/dist /usr/share/nginx/html" in dockerfile_text

    nginx_text = FRONTEND_NGINX_CONF.read_text(encoding="utf-8")
    assert "client_max_body_size 25M;" in nginx_text
    assert "gzip on;" in nginx_text
    assert "proxy_pass http://backend:8000/api/;" in nginx_text
    assert "try_files $uri $uri/ /index.html;" in nginx_text


def test_sp6_04_3_docker_compose_services_and_persistent_volumes() -> None:
    """[SP6-04.3 & SP6-04.4] Xác nhận docker-compose.yml kết nối 3 dịch vụ cùng volumes bền vững và hợp lệ."""
    assert DOCKER_COMPOSE_FILE.exists(), "Thiếu docker-compose.yml ở thư mục gốc"
    compose_text = DOCKER_COMPOSE_FILE.read_text(encoding="utf-8")

    # Kiểm tra đủ 3 dịch vụ: postgres, backend, frontend
    for service_decl in ("postgres:", "backend:", "frontend:"):
        assert service_decl in compose_text

    # Kiểm tra các ổ đĩa lưu trữ bền vững (Named Volumes) cho PostgreSQL, ChromaDB, Uploads và Model Cache
    for vol_decl in ("postgres_data:", "chroma_data:", "uploads_data:", "model_cache:"):
        assert vol_decl in compose_text

    assert "/var/lib/postgresql/data" in compose_text
    assert "/app/storage/chroma_db" in compose_text
    assert "/app/storage/uploads" in compose_text
    assert "/app/storage/model_cache" in compose_text

    # Nếu máy có cài đặt Docker CLI, chạy `docker compose config --quiet` để kiểm tra cú pháp chuẩn
    if shutil.which("docker"):
        proc = subprocess.run(
            ["docker", "compose", "-f", str(DOCKER_COMPOSE_FILE), "config", "--quiet"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"docker compose config thất bại: {proc.stderr}"
