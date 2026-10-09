"""The Kubernetes how-to tells the operator how not to log a reporter's IP address.

Below crit, ingress-nginx logs each rate-limited reporter's IP address. The chart's own
values and notes: the same guard in openwhistle/OpenWhistle.
"""

from tests.built_site import page


def test_the_kubernetes_docs_require_crit_error_logging_and_real_client_addresses() -> None:
    docs = page("/en/docs/kubernetes/")
    assert "limit-req-status-code" in docs
    # L4: proxy protocol or a local traffic policy; L7: forwarded headers
    # only with the trusted range, or clients spoof X-Forwarded-For.
    for setting in (
        "use-proxy-protocol",
        "externalTrafficPolicy: Local",
        "use-forwarded-headers",
        "proxy-real-ip-cidr",
    ):
        assert setting in docs, setting
