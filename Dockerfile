# zpostgresql — local audit container image for Camfrog AutoDJ.
#
# Reviewers and auditors use this image to run the project's test suite,
# lint, and format checks in a reproducible environment. It mirrors
# .github/workflows/tests.yml (Linux: python3-tk + xvfb for GUI tests).
#
# Build (from this repository root):
#   docker build -t zpostgresql:latest -t zpostgresql:audit .
#
# Run the audit:
#   docker run --rm zpostgresql:latest

FROM python:3.11-slim AS audit

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd -r autodj && useradd -r -g autodj -G autodj autodj

# Mirror .github/workflows/tests.yml (Linux): tkinter + virtual display for GUI tests.
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        python3-tk xvfb xauth \
    && rm -rf /var/lib/apt/lists/*

COPY . ./

RUN python -m pip install --upgrade pip setuptools && \
    python -m pip install -e ".[dev]" ruff mypy

# Build-time self-verification: the image is only usable when lint,
# format, and the full test suite pass.
RUN ruff check camfrog_autodj tests tools && \
    ruff format --check camfrog_autodj tests tools && \
    xvfb-run -a python -m pytest -q -p no:faulthandler -p no:cacheprovider tests

USER autodj
CMD ["sh", "-c", "xvfb-run -a python -m pytest -q -p no:faulthandler -p no:cacheprovider tests"]
