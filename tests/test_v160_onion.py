"""The onion how-to documents the private key, the shared rate limit and the trust boundary.

The onion service's own tests stay with the app in openwhistle/OpenWhistle.
"""

import re

import release_source

from tests.built_site import page


def test_onion_howto_warns_about_the_hidden_service_private_key() -> None:
    section = page("/en/docs/onion/")
    assert "hs_ed25519_secret_key" in section
    assert "0700" in section
    assert re.search(r"back(s|ing)? (it|the directory) up|back up", section, re.I)


def test_onion_howto_explains_the_shared_rate_limit_budget() -> None:
    section = page("/en/docs/onion/")
    assert "127.0.0.1" in section
    assert "429" in section


def test_onion_howto_and_security_section_explain_the_x_ow_onion_trust_boundary() -> None:
    """Both the how-to and the
    Security Architecture section must document that the app trusts nginx's
    X-OW-Onion header (never the client Host), and that this requires the
    app port to be reachable only through the shipped nginx."""
    howto = page("/en/docs/onion/")
    assert "X-OW-Onion" in howto
    assert "reachable only through" in howto

    security = page("/en/docs/onion-trust/")
    assert "X-OW-Onion" in security
    assert "Host" in security


def test_onion_location_is_a_documented_setting_of_the_release() -> None:
    assert "ONION_LOCATION" in release_source.settings()
    assert "ONION_LOCATION" in page("/en/docs/onion/")
