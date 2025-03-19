FROM ghcr.io/sdr-enthusiasts/docker-baseimage:base

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# hadolint ignore=DL3008,SC2086,DL4006,SC2039
RUN set -x && \
    TEMP_PACKAGES=() && \
    KEPT_PACKAGES=() && \
    # temp
    TEMP_PACKAGES+=() && \
    TEMP_PACKAGES+=(python3-pip) && \
    # keep
    KEPT_PACKAGES+=(python3-pip) && \
    KEPT_PACKAGES+=(python3-prctl) && \
    KEPT_PACKAGES+=(python3-bs4) && \
    KEPT_PACKAGES+=(python3-colorama) && \
    KEPT_PACKAGES+=(python3-requests) && \
    KEPT_PACKAGES+=(nodejs) && \
    KEPT_PACKAGES+=(npm) && \
    KEPT_PACKAGES+=(unzip) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    "${KEPT_PACKAGES[@]}" \
    "${TEMP_PACKAGES[@]}" \
    && \
    pip install --break-system-packages icao_nnumber_converter_us haversine javascript && \
    curl --location --output /tmp/BaseStation.zip https://github.com/rikgale/VRSData/raw/main/BaseStation.zip && \
    mkdir -p /opt/basestation && \
    unzip /tmp/BaseStation.zip -d /opt/basestation/ && \
    # Clean up
    apt-get autoremove -q -o APT::Autoremove::RecommendsImportant=0 -o APT::Autoremove::SuggestsImportant=0 -y ${TEMP_PACKAGES[@]} && \
    bash /scripts/clean-build.sh && \
    rm -rf /src/* /tmp/* /var/lib/apt/lists/*

COPY rootfs /
