
# ─────────────────────────────────────────────────────────────
# 基础镜像
# 用 slim 而不是 alpine：chromadb / onnxruntime 这些依赖在
# alpine(musl libc) 上没有现成 wheel，装起来要现场编译，代价远大于镜像体积收益。
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# ─────────────────────────────────────────────────────────────
# 运行时环境变量
# PYTHONUNBUFFERED  : 日志立即刷出，否则 docker logs 看不到实时输出
# PYTHONDONTWRITEBYTECODE : 不生成 .pyc，镜像更干净
# PIP_NO_CACHE_DIR  : 不保留 pip 缓存，省几十 MB
# ─────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ─────────────────────────────────────────────────────────────
# 依赖层：单独一层，利用构建缓存
# 只要 requirements.txt 内容没变，这一层直接复用，不会重装 60 多个包。
# 所以必须先 COPY requirements.txt，再 COPY 代码 —— 顺序不能反。
# ─────────────────────────────────────────────────────────────
COPY requirements.txt .

# 国内构建时用 --build-arg 覆盖成清华源，Dockerfile 本身保持通用
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install -r requirements.txt --index-url "$PIP_INDEX_URL"

# ─────────────────────────────────────────────────────────────
# 代码层
# .dockerignore 会挡掉 .venv / .env / __pycache__ 等不该进镜像的东西
# ─────────────────────────────────────────────────────────────
COPY . .

# 仅声明用途，不实际发布端口（真正的映射靠 docker run -p）
EXPOSE 8000

# exec 形式（JSON 数组）：容器 PID 1 直接是 python 进程，
# 能正确接收 SIGTERM，docker stop 才会干净退出。
# 写成 shell 形式（CMD python -m uvicorn ...）会多一层 sh，信号传不到。
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
