"""Leveled logging for acars2pos.

The script used to print unconditionally, which produced roughly five lines of
output per received message and made `docker logs` unusable. Every call site now
declares a severity and is filtered against a threshold read from the
environment.

Timestamps are deliberately not added here. The s6 service runs the script under
s6wrap --timestamps, so each line is already stamped by the supervisor; stamping
again would double it.

The level is read from MIN_LOG_LEVEL, which is the name the rest of the
sdr-enthusiasts fleet uses, or from LOG_LEVEL as an alias. Either a name
("info") or a number (4) is accepted, case-insensitively.

The default is TRACE, which reproduces the historical firehose exactly so that
existing deployments see no change when they upgrade. It is not the recommended
setting: MIN_LOG_LEVEL=4 keeps startup, connection and error reporting while
dropping the per-message output.
"""

from os import getenv
from pprint import pformat
from sys import stderr, stdout

FATAL = 1
ERROR = 2
WARN = 3
INFO = 4
DEBUG = 5
TRACE = 6

_NAMES = {
    "fatal": FATAL,
    "critical": FATAL,
    "error": ERROR,
    "err": ERROR,
    "warn": WARN,
    "warning": WARN,
    "info": INFO,
    "informational": INFO,
    "debug": DEBUG,
    "trace": TRACE,
    "all": TRACE,
}

# Historical behaviour printed everything, so that is what an unconfigured
# container must keep doing.
_DEFAULT = TRACE

_LABELS = {
    FATAL: "FATAL",
    ERROR: "ERROR",
    WARN: "WARN",
    INFO: "INFO",
    DEBUG: "DEBUG",
    TRACE: "TRACE",
}


def _parse(raw):
    """Map an env value to a threshold, returning (level, complaint_or_None)."""
    if raw is None:
        return _DEFAULT, None

    val = raw.strip()
    if not val:
        return _DEFAULT, None

    if val.lstrip("+-").isdigit():
        num = int(val)
        # Clamp rather than reject: a higher number means "even more verbose",
        # which is unambiguous, and 0 or below means "as quiet as possible".
        if num < FATAL:
            return FATAL, None
        if num > TRACE:
            return TRACE, None
        return num, None

    name = val.lower()
    if name in _NAMES:
        return _NAMES[name], None

    return _DEFAULT, f"unrecognised log level {raw!r}; using {_LABELS[_DEFAULT]}"


_raw = getenv("MIN_LOG_LEVEL")
if _raw is None:
    _raw = getenv("LOG_LEVEL")

level, _complaint = _parse(_raw)


def enabled(lvl):
    """True when lvl would be emitted.

    Callers use this to skip building a message that would only be discarded.
    Some of the suppressed output is expensive to produce -- regex substitution
    over message text, and a full recount of per-type totals -- so the guard is
    what actually saves the work rather than merely hiding it.
    """
    return lvl <= level


def _emit(lvl, msg, stream):
    if enabled(lvl):
        print(msg, file=stream)


def fatal(msg, stream=stderr):
    _emit(FATAL, msg, stream)


def error(msg, stream=stderr):
    _emit(ERROR, msg, stream)


def warn(msg, stream=stderr):
    _emit(WARN, msg, stream)


def info(msg, stream=stdout):
    _emit(INFO, msg, stream)


def debug(msg, stream=stdout):
    _emit(DEBUG, msg, stream)


def trace(msg, stream=stdout):
    _emit(TRACE, msg, stream)


def pp(lvl, obj, stream=stdout, sort_dicts=True):
    """pprint an object, but only when lvl passes the threshold."""
    if enabled(lvl):
        print(pformat(obj, sort_dicts=sort_dicts), file=stream)


if _complaint:
    warn(_complaint)
