"""Guard against importing bitcoin_api from a different checkout."""

from pathlib import Path


def test_bitcoin_api_import_resolves_to_current_checkout():
    """Tests should import bitcoin_api from this checkout's src directory."""
    import bitcoin_api

    repo_root = Path(__file__).resolve().parents[1]
    module_path = Path(bitcoin_api.__file__).resolve()

    assert module_path.is_relative_to(repo_root), (
        f"bitcoin_api imported from unexpected path: {module_path}"
    )
