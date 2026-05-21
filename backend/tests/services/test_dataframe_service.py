from io import BytesIO
from uuid import uuid4

import pandas as pd
import pytest
from starlette.datastructures import UploadFile

from app.services import dataframe_chat_service
from app.services.dataframe_chat_service import ask_dataframe_question, store_uploaded_dataframe
from app.services.dataframe_service import normalize_dataframe


def test_normalize_dataframe_deduplicates_and_strips_columns() -> None:
    import pandas as pd

    dataframe = pd.DataFrame(
        [[1, 2, None], [3, 4, None]],
        columns=[" Revenue ", "Revenue", "   "],
    )

    normalized = normalize_dataframe(dataframe)

    assert normalized.columns.tolist() == ["Revenue", "Revenue_2"]
    assert len(normalized) == 2


@pytest.mark.asyncio
async def test_store_uploaded_dataframe_and_query(monkeypatch: pytest.MonkeyPatch) -> None:
    dataframe_chat_service._DATAFRAME_SESSIONS.clear()

    async def _run() -> None:
        upload = UploadFile(
            filename="employees.csv",
            file=BytesIO(b"name,salary\nAna,100\nBen,200\n"),
            headers={"content-type": "text/csv"},
        )

        current_user = type(
            "UserStub",
            (),
            {"id": uuid4(), "email": "tester@example.com"},
        )()

        monkeypatch.setattr(
            dataframe_chat_service,
            "invoke_pandas_agent",
            lambda dataframe, question, user_email: {"output": f"{question} for {len(dataframe)} rows by {user_email}"},
        )

        source = await store_uploaded_dataframe(current_user, upload)
        result = await ask_dataframe_question(current_user, "highest salary")

        assert source["row_count"] == 2
        assert source["columns"] == ["name", "salary"]
        assert result["answer"] == "highest salary for 2 rows by tester@example.com"
        assert result["row_count"] == 2

    await _run()


@pytest.mark.asyncio
async def test_sum_question_uses_deterministic_numeric_total(monkeypatch: pytest.MonkeyPatch) -> None:
    dataframe_chat_service._DATAFRAME_SESSIONS.clear()

    current_user = type(
        "UserStub",
        (),
        {"id": uuid4(), "email": "tester@example.com"},
    )()

    dataframe_chat_service._DATAFRAME_SESSIONS[current_user.id] = dataframe_chat_service.UserDataframeSession(
        dataframe=pd.DataFrame(
            {
                "Product_Name": ["Phone", "Laptop", "Watch"],
                "Price": ["79,999", "55,999", "19,999"],
            }
        ),
        source_type="google-sheet",
        source_name="test-sheet",
        updated_at=pd.Timestamp.now(tz="UTC").to_pydatetime(),
    )

    monkeypatch.setattr(
        dataframe_chat_service,
        "invoke_pandas_agent",
        lambda *_args, **_kwargs: pytest.fail("Agent should not run for deterministic SUM question"),
    )

    result = await ask_dataframe_question(current_user, "SUM of the product prices")

    assert result["answer"] == "The sum of Price is 155,997."