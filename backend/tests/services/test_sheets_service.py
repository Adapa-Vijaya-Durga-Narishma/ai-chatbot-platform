import pytest

from app.services.sheets_service import (
    SheetLoadError,
    _extract_multiline_json_value,
    _load_credentials_from_file,
)


def test_extracts_multiline_google_service_account_json() -> None:
    env_text = """
APP_NAME=amzur-ai-chat
GOOGLE_SERVICE_ACCOUNT_JSON={
  "type": "service_account",
  "client_email": "bot@example.com"
}
MAX_UPLOAD_MB=20
""".strip()

    extracted = _extract_multiline_json_value(env_text, "GOOGLE_SERVICE_ACCOUNT_JSON")

    assert extracted is not None
    assert '"type": "service_account"' in extracted
    assert '"client_email": "bot@example.com"' in extracted


def test_returns_none_when_variable_missing() -> None:
    env_text = "APP_NAME=amzur-ai-chat\nMAX_UPLOAD_MB=20"

    extracted = _extract_multiline_json_value(env_text, "GOOGLE_SERVICE_ACCOUNT_JSON")

    assert extracted is None


def test_load_credentials_from_file_reads_valid_json(tmp_path) -> None:
    credentials_file = tmp_path / "service-account.json"
    credentials_file.write_text(
        '{"type":"service_account","client_email":"bot@example.com"}',
        encoding="utf-8",
    )

    credentials = _load_credentials_from_file(str(credentials_file))

    assert credentials is not None
    assert credentials["client_email"] == "bot@example.com"


def test_load_credentials_from_file_raises_for_invalid_json(tmp_path) -> None:
    credentials_file = tmp_path / "service-account.json"
    credentials_file.write_text("not-json", encoding="utf-8")

    with pytest.raises(SheetLoadError, match="valid service account JSON file"):
        _load_credentials_from_file(str(credentials_file))
