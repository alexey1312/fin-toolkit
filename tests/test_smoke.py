"""Smoke test to verify pytest setup."""


def test_import() -> None:
    """Verify fin_toolkit can be imported."""
    import fin_toolkit

    assert fin_toolkit.__version__ == "0.1.0"
