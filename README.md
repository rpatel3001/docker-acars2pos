# docker-acars2pos
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/rpatel3001/docker-acars2pos/deploy.yml?branch=master)](https://github.com/rpatel3001/docker-acars2pos/actions/workflows/deploy.yml)
[![Discord](https://img.shields.io/discord/734090820684349521)](https://discord.gg/sTf9uYF)

A Docker image which ingests JSON formatted ACARS, VDLM2, and HFDL messages and parses them for position data. Any positions found are output on a TCP port in SBS/Basestation format.

Under active development, everything is subject to change without notice.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JSON_IN`   | Semi-colon separated list of `host:port` entries to connect to for JSON ingest. | acars_router:15550 |
| `SBS_OUT`   | Semi-colon separated list of `host:port` entries to connect to for SBS/Basestation output. | ultrafeeder:12000 |
| `LOG_FILE`  | Set to any value to message text, type, SBS output, and adsbexchange link to files in `/log`. | Unset |
| `LAT`       | Latitude of receiver. Only required if `MAX_DIST` > 0 | Unset |
| `LON`       | Longitude of receiver. Only required if `MAX_DIST` > 0 | Unset |
| `MAX_DIST`  | Set this to a nonzero value to reject parsed positions that are too far away. Only applies to positions parsed from message text. | `0` |
| `DIST_UNIT` | The unit of the value in `MAX_DIST`. One of `km`, `m`, `mi`, `nmi`, `ft`, `in`. | `nmi` |
| `SEND_ALL`  | Set to any value to send SBS messages for messages without a position. Set to `log` to also print a log entry for each non-position message. | Unset |

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
      - LOG_FILE=true
    volumes:
      - ./logs:/log
```
