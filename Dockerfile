FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY requirements.txt /tmp

# hadolint ignore=DL3008,SC2086,DL4006,SC2039
RUN set -x && \
#    TEMP_PACKAGES=() && \
#    KEPT_PACKAGES=() && \
#    # temp
#    TEMP_PACKAGES+=() && \
#    # keep
#    KEPT_PACKAGES+=() && \
#    apt-get update && \
#    apt-get install -y --no-install-recommends \
#    "${KEPT_PACKAGES[@]}" \
#    "${TEMP_PACKAGES[@]}" \
#    && \
    pip install --break-system-packages -r /tmp/requirements.txt && \
    # Clean up
#    apt-get remove -y "${TEMP_PACKAGES[@]}" && \
#    apt-get autoremove -y && \
    rm -rf /src/* /tmp/* /var/lib/apt/lists/*

COPY rootfs /
