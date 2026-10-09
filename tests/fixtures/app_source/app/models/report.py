import enum


class ReportStatus(enum.StrEnum):
    received = "received"
    closed = "closed"


STATUS_TRANSITIONS: dict[str, set[str]] = {
    "received": {"closed"},
    "closed": {"received"},
}
