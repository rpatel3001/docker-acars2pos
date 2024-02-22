FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008,SC2086,DL4006,SC2039
RUN set -x && \
    TEMP_PACKAGES=() && \
    KEPT_PACKAGES=() && \
    # temp
    TEMP_PACKAGES+=() && \
    # keep
    KEPT_PACKAGES+=(python3-prctl) && \
    KEPT_PACKAGES+=(python3-bs4) && \
    KEPT_PACKAGES+=(python3-colorama) && \
    KEPT_PACKAGES+=(python3-requests) && \
    KEPT_PACKAGES+=(unzip) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    "${KEPT_PACKAGES[@]}" \
    "${TEMP_PACKAGES[@]}" \
    && \
    pip install --break-system-packages icao_nnumber_converter_us && \
    curl --location --output /tmp/BaseStation.zip https://github.com/rikgale/VRSData/raw/main/BaseStation.zip && \
    mkdir -p /opt/basestation && \
    unzip /tmp/BaseStation.zip -d /opt/basestation/ && \
    # Clean up
    apt-get remove -y "${TEMP_PACKAGES[@]}" && \
    apt-get autoremove -y && \
    rm -rf /src/* /tmp/* /var/lib/apt/lists/*

COPY rootfs /
