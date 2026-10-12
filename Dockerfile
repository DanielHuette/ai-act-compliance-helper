# Three stages so the final image holds only what runs: no compiler, pip cache or download tools.

ARG PYTHON_VERSION=3.13-slim

FROM python:${PYTHON_VERSION} AS dependencies

ARG WITH_SEARCH_MODEL=1

RUN apt-get update \
 && apt-get install --yes --no-install-recommends build-essential libxml2-dev libxslt1-dev \
 && rm -rf /var/lib/apt/lists/*

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml constraints.txt README.md LICENSE NOTICE AUTHORS.md ./
COPY src/ ./src/

# Exact versions from constraints.txt. CPU-only torch: the CUDA build is 2.5 GB larger and useless
# without a GPU.
RUN if [ "$WITH_SEARCH_MODEL" = "1" ]; then \
      pip install --constraint constraints.txt \
        --extra-index-url https://download.pytorch.org/whl/cpu ".[search]" ; \
    else \
      pip install --constraint constraints.txt "." ; \
    fi

# The models ship in the image: the bundled indexes were embedded with bge-m3, so offline queries
# must be embedded by the same model, and purpose matching needs the bge cross-encoder.
# WITH_SEARCH_MODEL=0 builds a small image with the fallback embedder and no purpose matching.
FROM dependencies AS models

ARG WITH_SEARCH_MODEL=1
ARG EMBEDDING_MODEL=BAAI/bge-m3
ARG RERANKER_MODEL=BAAI/bge-reranker-v2-m3
ENV HF_HOME=/opt/models \
    HF_HUB_DISABLE_TELEMETRY=1

# Full snapshots on purpose (bge-m3: 4.58 GB instead of 2.31 GB): a partial one is rejected offline
# by huggingface_hub as incomplete and search silently falls back. Fails if weights < 100 MB.
RUN mkdir -p /opt/models \
 && if [ "$WITH_SEARCH_MODEL" != "1" ]; then \
      echo "built without models; fallback embedder, purpose matching off" > /opt/models/NOTE.txt ; \
    else \
      for model in "$EMBEDDING_MODEL" "$RERANKER_MODEL"; do \
        python -c "import sys; from pathlib import Path; \
from huggingface_hub import snapshot_download; \
name = sys.argv[1]; folder = Path(snapshot_download(name)); \
weights = [d for d in folder.glob('*') if d.name in ('pytorch_model.bin','model.safetensors')]; \
size = sum(d.stat().st_size for d in weights); \
sys.exit('Model %s fetched incompletely: weights %d bytes. Present: %s' % (name, size, sorted(q.name for q in folder.glob('*')))) if size < 100*1024*1024 else None; \
print('Model %s complete: %.2f GB weights, snapshot %.2f GB' % (name, size/1e9, sum(d.stat().st_size for d in folder.rglob('*') if d.is_file())/1e9))" "$model" \
        || exit 1 ; \
      done ; \
    fi

FROM python:${PYTHON_VERSION}

ARG WITH_SEARCH_MODEL=1

LABEL org.opencontainers.image.title="AI Act Compliance Helper" \
      org.opencontainers.image.description="Cited answers on the EU AI Act (Regulation (EU) 2024/1689) and the GDPR. Not legal advice." \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/DanielHuette/ai-act-compliance-helper"

# curl serves the HEALTHCHECK from inside the container.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends libxml2 libxslt1.1 curl \
 && rm -rf /var/lib/apt/lists/* \
 # Fixed UID/GID 10001 keeps permissions on mounted directories identical on every host.
 && groupadd --gid 10001 app \
 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin app

COPY --from=dependencies /opt/venv /opt/venv
# Owned by the service user: model libraries write lock files there ("corrupted file" otherwise).
COPY --from=models --chown=10001:10001 /opt/models /opt/models

WORKDIR /app

# Root-owned and read-only, so code execution in the service cannot persist via its sources.
COPY --chown=0:0 src/ /app/src/
COPY --chown=0:0 data/ /app/data/
COPY --chown=0:0 pyproject.toml README.md /app/
COPY --chown=0:0 web/ /app/web/
RUN chmod -R a-w /app/src /app/data /app/web /app/pyproject.toml /app/README.md

# PYTHONPATH=/app/src on purpose: paths.root() resolves data relative to the source tree, which
# finds /app/data; the installed copy in site-packages would not.
ENV PYTHONPATH=/app/src \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/opt/models \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    COMPLIANCE_HELPER_HOST=0.0.0.0 \
    COMPLIANCE_HELPER_PORT=8000 \
    COMPLIANCE_HELPER_REQUESTS_PER_MINUTE=30 \
    COMPLIANCE_HELPER_CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000 \
    COMPLIANCE_HELPER_MODEL=auto \
    COMPLIANCE_HELPER_BUILD_INDEX=0

# Without the bundled models, loading them would hang on the network: the small image picks the
# fallback embedder and switches purpose matching off unless COMPLIANCE_HELPER_RERANK is set. Left
# empty in the full image, COMPLIANCE_HELPER_RERANK keeps purpose matching on and the slow search
# reranking off.
RUN if [ "$WITH_SEARCH_MODEL" = "1" ]; then \
      printf '%s\n' 'COMPLIANCE_HELPER_EMBEDDING=BAAI/bge-m3' \
        'COMPLIANCE_HELPER_RERANK=${COMPLIANCE_HELPER_RERANK:-}' > /app/.model_choice ; \
    else \
      printf '%s\n' 'COMPLIANCE_HELPER_EMBEDDING=hashing-fallback' \
        'COMPLIANCE_HELPER_RERANK=${COMPLIANCE_HELPER_RERANK:-0}' > /app/.model_choice ; \
    fi \
 && chown 0:0 /app/.model_choice \
 && chmod 0444 /app/.model_choice
ENV COMPLIANCE_HELPER_EMBEDDING=""

USER 10001:10001

EXPOSE 8000

# A service without corpus still answers, so "not_ready" counts as unhealthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=180s --retries=3 \
  CMD curl --fail --silent http://127.0.0.1:8000/health \
      | grep -q -e '"status":"ready"' -e '"status":"degraded"' || exit 1

CMD ["sh", "-c", ". /app/.model_choice && export COMPLIANCE_HELPER_EMBEDDING COMPLIANCE_HELPER_RERANK && exec compliance-helper serve --address \"$COMPLIANCE_HELPER_HOST\" --port \"$COMPLIANCE_HELPER_PORT\""]
