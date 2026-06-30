FROM ghcr.io/home-assistant/base:latest
ARG BUILD_VERSION
ARG BUILD_ARCH
ARG REPOSITORY=https://github.com/marksalama/Home-Assistant.git

LABEL \
    io.hass.version="${BUILD_VERSION}" \
    io.hass.type="app" \
    io.hass.arch="${BUILD_ARCH}"

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apk add --no-cache \
    bash \
    build-base \
    git \
    libffi-dev \
    openssl-dev \
    py3-pip \
    python3 \
    python3-dev

RUN python3 -m venv /opt/ha-mcp \
    && /opt/ha-mcp/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/ha-mcp/bin/pip install --no-cache-dir "home-assistant-mcp[yaml] @ git+${REPOSITORY}@main"

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
