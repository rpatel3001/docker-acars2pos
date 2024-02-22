# docker-acars2pos
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/rpatel3001/docker-acars2pos/deploy.yml?branch=master)](https://github.com/rpatel3001/docker-acars2pos/actions/workflows/deploy.yml)
[![Discord](https://img.shields.io/discord/734090820684349521)](https://discord.gg/sTf9uYF)

A Docker image which ingests JSON formatted ACARS, VDLM2, and HFDL messages and parses them for position data. Any positions found are output on a TCP port in SBS/Basestation format.

Under active development, everything is subject to change without notice.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JSON_IN` | Semi-colon separated list of `host:port` entries to connect to for JSON ingest. | acars_router:15550 |
| `SBS_OUT` | Semi-colon separated list of `host:port` entries to connect to for SBS/Basestation output. | ultrafeeder:12000 |

## Docker Compose

```
services:
  acars2pos:
    container_name: acars2pos
    hostname: acars2pos
    image: ghcr.io/rpatel3001/docker-acars2pos
    restart: always
    environment:
      - JSON_IN=planeslxc:15550;planeslxc:15555;planeslxc:15556
      - SBS_OUT=adsbpc:12002;adsbpc:12004
```
