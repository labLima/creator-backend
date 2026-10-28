from __future__ import annotations

from collections import defaultdict
from threading import Lock

HTTP_DURATION_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class MetricsRegistry:
    """Small Prometheus exposition registry with intentionally bounded labels."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_requests: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_errors: dict[tuple[str, str, str], int] = defaultdict(int)
        self._http_duration_counts: dict[tuple[str, str, float | None], int] = defaultdict(int)
        self._http_duration_sums: dict[tuple[str, str], float] = defaultdict(float)
        self._lock = Lock()

    def increment(self, *, rate_class: str, endpoint: str, outcome: str) -> None:
        with self._lock:
            self._counters[(rate_class, endpoint, outcome)] += 1

    def observe_http_request(
        self,
        *,
        method: str,
        route: str,
        status: int,
        duration_seconds: float,
    ) -> None:
        status_label = str(status)
        with self._lock:
            self._http_requests[(method, route, status_label)] += 1
            if status >= 400:
                self._http_errors[(method, route, status_label)] += 1
            self._http_duration_sums[(method, route)] += duration_seconds
            for bucket in HTTP_DURATION_BUCKETS:
                if duration_seconds <= bucket:
                    self._http_duration_counts[(method, route, bucket)] += 1
            self._http_duration_counts[(method, route, None)] += 1

    def render(self) -> str:
        with self._lock:
            counters = sorted(self._counters.items())
            http_requests = sorted(self._http_requests.items())
            http_errors = sorted(self._http_errors.items())
            duration_counts = dict(self._http_duration_counts)
            duration_sums = dict(self._http_duration_sums)

        lines = [
            "# HELP creator_http_requests_total HTTP requests completed.",
            "# TYPE creator_http_requests_total counter",
        ]
        for (method, route, status), value in http_requests:
            lines.append(
                "creator_http_requests_total{"
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",'
                f'status="{_escape_label(status)}"}} {value}'
            )
        lines.extend(
            [
                "# HELP creator_http_errors_total HTTP requests completed with an error status.",
                "# TYPE creator_http_errors_total counter",
            ]
        )
        for (method, route, status), value in http_errors:
            lines.append(
                "creator_http_errors_total{"
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",'
                f'status="{_escape_label(status)}"}} {value}'
            )
        lines.extend(
            [
                "# HELP creator_http_request_duration_seconds HTTP request duration.",
                "# TYPE creator_http_request_duration_seconds histogram",
            ]
        )
        duration_keys = sorted({(method, route) for method, route, _ in duration_counts})
        for method, route in duration_keys:
            for bucket in HTTP_DURATION_BUCKETS:
                cumulative = duration_counts.get((method, route, bucket), 0)
                lines.append(
                    "creator_http_request_duration_seconds_bucket{"
                    f'method="{_escape_label(method)}",'
                    f'route="{_escape_label(route)}",'
                    f'le="{bucket}"}} {cumulative}'
                )
            count = duration_counts[(method, route, None)]
            lines.append(
                "creator_http_request_duration_seconds_bucket{"
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",le="+Inf"}} {count}'
            )
            lines.append(
                "creator_http_request_duration_seconds_count{"
                f'method="{_escape_label(method)}",route="{_escape_label(route)}"}} {count}'
            )
            lines.append(
                "creator_http_request_duration_seconds_sum{"
                f'method="{_escape_label(method)}",route="{_escape_label(route)}"}} '
                f"{duration_sums[(method, route)]}"
            )
        lines.extend(
            [
                "# HELP creator_rate_limit_requests_total Rate limiter decisions.",
                "# TYPE creator_rate_limit_requests_total counter",
            ]
        )
        for (rate_class, endpoint, outcome), value in counters:
            lines.append(
                "creator_rate_limit_requests_total{"
                f'class="{_escape_label(rate_class)}",'
                f'endpoint="{_escape_label(endpoint)}",'
                f'outcome="{_escape_label(outcome)}"}} {value}'
            )
        return "\n".join(lines) + "\n"

    @property
    def content_type(self) -> str:
        return "text/plain; version=0.0.4; charset=utf-8"
