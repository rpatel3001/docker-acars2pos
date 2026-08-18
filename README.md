# docker-acars2pos
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/rpatel3001/docker-acars2pos/deploy.yml?branch=master)](https://github.com/rpatel3001/docker-acars2pos/actions/workflows/deploy.yml)
[![Discord](https://img.shields.io/discord/734090820684349521)](https://discord.gg/sTf9uYF)

A Docker image which ingests JSON formatted ACARS, VDLM2, and HFDL messages and parses them for position data. Any positions found are output on a TCP port in SBS/Basestation format.

Under active development, everything is subject to change without notice.

Squawk Codes:
* First Digit
  * 1 = ACARS
  * 3 = VDL
  * 4 = VDL XID position
  * 5 = HFDL
  * 6 = HFDL position
* Second Digit
  * 0 = message not decoded by airframes library
  * 1 = message decoded by airframes library
  * 2 = message decoded by airframes library with position
* Third Digit
  * 0 = no position from python regexes
  * 1 = position from matching message label regex
  * 2 = position from a different message label regex
  * 3 = position from unlabeled regex

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `JSON_IN`   | Semi-colon separated list of `host:port` entries to connect to for JSON ingest. | acars_router:15550 |
| `SBS_OUT`   | Semi-colon separated list of `host:port` entries to connect to for SBS/Basestation output. | ultrafeeder:12000 |
| `MIN_LOG_LEVEL` | Minimum severity to log. See [Logging](#logging). | `6` (log everything) |
| `LOG_FILE`  | Set to any value to message text, type, SBS output, and adsbexchange link to files in `/log`. | Unset |
| `LAT`       | Latitude of receiver. Only required if `MAX_DIST` > 0 | Unset |
| `LON`       | Longitude of receiver. Only required if `MAX_DIST` > 0 | Unset |
| `MAX_DIST`  | Set this to a nonzero value to reject parsed positions that are too far away. Only applies to positions parsed from message text. | `0` |
| `DIST_UNIT` | The unit of the value in `MAX_DIST`. One of `km`, `m`, `mi`, `nmi`, `ft`, `in`. | `nmi` |
| `SEND_ALL`  | Set to any value to send SBS messages for messages without a position. Set to `log` to also print a log entry for each non-position message. | Unset |
| `ACARS_FREQ_AS_SQUAWK`, `VDLM2_FREQ_AS_SQUAWK`, `HFDL_FREQ_AS_SQUAWK`  | Set to any value to send the received frequency as the squawk value, for each incoming message type. | Unset |
| `ACARS_FREQ_AS_ALT`, `VDLM2_FREQ_AS_ALT`, `HFDL_FREQ_AS_ALT`  | Set to any value to send the received frequency as the altitude value, for each incoming message type. | Unset |

## Logging

By default this container logs every message it decodes, which works out to
roughly five lines of output per received message and makes `docker logs`
impractical to read. `MIN_LOG_LEVEL` sets the minimum severity that is printed.

| Value | Name    | What it adds                                                             |
|-------|---------|--------------------------------------------------------------------------|
| `1`   | `fatal` | Only errors that stop the script.                                        |
| `2`   | `error` | Failures decoding a message.                                             |
| `3`   | `warn`  | Lost or refused connections, malformed input.                            |
| `4`   | `info`  | Startup and connect/reconnect messages. Recommended.                     |
| `5`   | `debug` | Tracebacks, and the message behind a decode failure.                     |
| `6`   | `trace` | Every decoded message, position and running per-type tally. The default. |

Either the number or the name may be used, and `LOG_LEVEL` is accepted as an
alias for `MIN_LOG_LEVEL`. Each level includes everything above it in the table.

The default is `6` so that upgrading changes nothing. `MIN_LOG_LEVEL=4` is the
useful setting for a normal deployment: it keeps startup and connection
reporting, plus anything that goes wrong, and drops the per-message output.
Measured against a corpus of 4148 real messages, that reduces the log from
22254 lines to 30.

The log level has no effect on the SBS/Basestation messages the container
produces, nor on the files written when `LOG_FILE` is set.

## Docker Compose

```yaml
services:
  acars2pos:
    container_name: acars2pos
    hostname: acars2pos
    image: ghcr.io/rpatel3001/docker-acars2pos
    restart: always
    environment:
      - JSON_IN=acars_router:15550;acars_router:15555;acars_router:15556
      - SBS_OUT=tar1090acars:12000
      - MIN_LOG_LEVEL=4
      - LOG_RAW=true
#      - LOG_FILE=true
      - MAX_DIST=201
      - LAT=aa.bb
      - LON=-xx.yy
#      - SEND_ALL=true
```
