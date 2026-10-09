"""The virus-scan how-to warns that the Helm chart ships no clamd (v1.6.0).

The scanner's own tests stay with the app in openwhistle/OpenWhistle.
"""

from tests.built_site import page


def test_virus_scan_docs_warn_that_helm_ships_no_clamd() -> None:
    """The chart deploys no clamav pod; enabling CLAMAV_HOST via Helm without
    pointing it at a real, reachable clamd fails every upload closed. RED if
    this warning is ever removed from the how-to."""
    section = page("/en/docs/clamav/")
    assert "Helm" in section
    assert "no clamav pod" in section
    assert "clamavHost" in section
    assert "reachable" in section and "refused" in section
