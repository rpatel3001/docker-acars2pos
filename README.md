# docker-acars2pos
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/rpatel3001/docker-acars2pos/Build%20and%20deploy%20to%20ghcr.io)](https://github.com/rpatel3001/docker-acars2pos/actions/workflows/deploy.yml)
[![Discord](https://img.shields.io/discord/734090820684349521)](https://discord.gg/sTf9uYF)

A Docker image which ingests JSON formatted ACARS, VDLM2, and HFDL messages and parses them for position data. Any positions found are output on a TCP port in SBS/Basestation format.

Under active development, everything is subject to change without notice.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ACARS_HOST`  | Host to connect to for ACARS ingest. | acars_router |
| `ACARS_PORT`  | Port to connect to for ACARS ingest. | 15550 |
| `VDLM2_HOST`  | Host to connect to for VDLM2 ingest. | acars_router |
| `VDLM2_PORT`  | Port to connect to for VDLM2 ingest. | 15555 |
| `HFDL_HOST`   | Host to connect to for HFDL ingest.  | acars_router |
| `HFDL_PORT`   | Port to connect to for HFDL ingest.  | 15556 |
| `SBS_HOST`    | Host to connect to for SBS output.   | ultrafeeder |
| `SBS_PORT`    | Port to connect to for SBS output.   | 12000 |

## Docker

`docker run --rm ghcr.io/rpatel3001/docker-acars2pos`
