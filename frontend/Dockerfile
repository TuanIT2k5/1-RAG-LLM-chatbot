# ==============================================================================
# [SP6-04.2] Dockerfile Multi-stage cho Frontend (Node.js 20 Builder + Nginx Alpine)
# ==============================================================================

# ------------------------------------------------------------------------------
# Giai đoạn 1 (Stage 1): Biên dịch mã nguồn TypeScript & đóng gói Vite (Builder)
# ------------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

# Cho phép truyền biến môi trường VITE_API_BASE_URL lúc build (mặc định: /api qua Nginx Proxy)
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Sao chép package.json và package-lock.json trước để lưu đệm (cache) node_modules
COPY package.json package-lock.json* ./
RUN npm ci

# Sao chép toàn bộ mã nguồn giao diện và thực thi bản dựng Production
COPY . .
RUN npm run build

# ------------------------------------------------------------------------------
# Giai đoạn 2 (Stage 2): Máy chủ Web Nginx siêu nhẹ phục vụ giao diện tốc độ cao
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS production

LABEL maintainer="Intelligent Document Chatbot Team"
LABEL description="Nginx Production Server for React 18 + Tailwind CSS Frontend"

# Sao chép cấu hình Nginx tùy chỉnh (hỗ trợ Gzip, SPA routing và Reverse Proxy /api)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Sao chép gói tài nguyên tĩnh đã tối ưu hóa từ giai đoạn Builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
