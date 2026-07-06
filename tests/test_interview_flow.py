import pytest

from src.utils.interview_flow import (
    interview_fields_complete,
    next_interview_field,
    parse_interview_field,
)


@pytest.mark.parametrize(
    "field,value,expected",
    [
        ("monthly_income", "R$ 8.000,00", 8000.0),
        ("monthly_income", "5000", 5000.0),
        ("job_type", "formal", "formal"),
        ("job_type", "autônomo", "autônomo"),
        ("monthly_expenses", "1500", 1500.0),
        ("dependents", "2", 2),
        ("has_debts", "sim", True),
        ("has_debts", "não", False),
    ],
)
def test_parse_interview_field_valid(field, value, expected):
    parsed, error = parse_interview_field(field, value)
    assert error is None
    assert parsed == expected


def test_interview_progression():
    collected = {}
    assert next_interview_field(collected) == "monthly_income"
    collected["monthly_income"] = 5000.0
    assert next_interview_field(collected) == "job_type"
    collected.update(
        {
            "job_type": "formal",
            "monthly_expenses": 1000.0,
            "dependents": 1,
            "has_debts": False,
        }
    )
    assert interview_fields_complete(collected) is True
    assert next_interview_field(collected) is None
