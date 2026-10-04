import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from config import FINANCIAL_TOLERANCE_PERCENT, MAX_DTI, MAX_LTV, MIN_CREDIT_SCORE


MONEY_QUANTUM = Decimal("0.01")


class FinancialValidationError(ValueError):
    pass


@dataclass
class Comparison:
    field_name: str
    application_value: str | None
    document_value: str | None
    difference: float | None
    difference_percentage: float | None
    status: str
    description: str
    source_document_id: str | None = None


def _decimal(value: Any, field_name: str) -> Decimal:
    if value is None or value == "":
        raise FinancialValidationError(f"{field_name} is missing.")
    try:
        number = Decimal(str(value).replace(",", "").replace("₹", "").replace("$", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise FinancialValidationError(f"{field_name} must be a valid number.") from exc
    if not number.is_finite():
        raise FinancialValidationError(f"{field_name} must be finite.")
    return number


def validate_income(value: Any) -> Decimal:
    number = _decimal(value, "Monthly gross income")
    if number <= 0:
        raise FinancialValidationError("Monthly gross income must be greater than zero.")
    return number


def validate_debt(value: Any) -> Decimal:
    number = _decimal(value, "Existing monthly debt")
    if number < 0:
        raise FinancialValidationError("Existing monthly debt cannot be negative.")
    return number


def validate_loan_amount(value: Any) -> Decimal:
    number = _decimal(value, "Requested loan amount")
    if number <= 0:
        raise FinancialValidationError("Requested loan amount must be greater than zero.")
    return number


def validate_property_value(value: Any) -> Decimal:
    number = _decimal(value, "Property value")
    if number <= 0:
        raise FinancialValidationError("Property value must be greater than zero.")
    return number


def calculate_dti(monthly_debt: Any, monthly_income: Any) -> Decimal:
    income = validate_income(monthly_income)
    debt = validate_debt(monthly_debt)
    return ((debt / income) * Decimal("100")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_ltv(loan_amount: Any, property_value: Any) -> Decimal:
    loan = validate_loan_amount(loan_amount)
    property_value_decimal = validate_property_value(property_value)
    return ((loan / property_value_decimal) * Decimal("100")).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _display(value: Any) -> str:
    return str(value) if value is not None else "Missing"


def _field_value(fields: dict[str, Any], *names: str) -> tuple[Any, str | None]:
    for name in names:
        field = fields.get(name)
        if isinstance(field, dict) and field.get("value") not in (None, ""):
            source = field.get("source") or {}
            return field["value"], source.get("document_id")
    return None, None


def _numeric_from_any(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    matches = re.findall(r"-?\d[\d,]*(?:\.\d+)?", str(value))
    if not matches:
        return None
    try:
        return Decimal(matches[0].replace(",", ""))
    except InvalidOperation:
        return None


def compare_value(field_name: str, application_value: Any, document_value: Any, source_document_id: str | None = None) -> Comparison:
    app_number = _numeric_from_any(application_value)
    doc_number = _numeric_from_any(document_value)
    if app_number is None or doc_number is None:
        status = "Verified Match" if str(application_value).strip().casefold() == str(document_value).strip().casefold() else "Needs Review"
        return Comparison(field_name, _display(application_value), _display(document_value), None, None, status, f"{field_name} differs between sources." if status == "Needs Review" else f"{field_name} matches.", source_document_id)
    difference = abs(app_number - doc_number)
    percentage = (difference / abs(app_number) * Decimal("100")) if app_number else Decimal("100")
    status = "Verified Match" if difference == 0 else "Minor Difference" if percentage <= FINANCIAL_TOLERANCE_PERCENT else "Needs Review"
    description = f"{field_name}: application value {_display(application_value)}, document value {_display(document_value)}, difference {difference.quantize(MONEY_QUANTUM)}."
    return Comparison(field_name, _display(application_value), _display(document_value), float(difference.quantize(MONEY_QUANTUM)), float(percentage.quantize(MONEY_QUANTUM)), status, description, source_document_id)


def build_validation_result(application: Any, analyzed_documents: list[dict[str, Any]]) -> dict[str, Any]:
    income = validate_income(application.monthly_income)
    debt = validate_debt(application.monthly_debt)
    loan = validate_loan_amount(application.loan_amount)
    property_value = validate_property_value(application.property_value)
    dti = calculate_dti(debt, income)
    ltv = calculate_ltv(loan, property_value)
    issues: list[Comparison] = []
    missing: list[str] = []
    policy_issues: list[Comparison] = []

    if loan > property_value:
        issues.append(Comparison("Loan Amount", str(loan), str(property_value), float(loan - property_value), None, "Needs Review", "Requested loan amount is greater than property value. Human verification required."))
    if MAX_DTI is not None and dti > MAX_DTI:
        policy_issues.append(Comparison("DTI", str(application.monthly_income), str(dti), None, None, "Policy Review Required", f"DTI {dti}% exceeds configured demonstration threshold {MAX_DTI}%."))
    if MAX_LTV is not None and ltv > MAX_LTV:
        policy_issues.append(Comparison("LTV", str(application.property_value), str(ltv), None, None, "Policy Review Required", f"LTV {ltv}% exceeds configured demonstration threshold {MAX_LTV}%."))

    income_comparisons = []
    names = []
    credit_score = None
    for document in analyzed_documents:
        fields = document.get("structured_fields") or {}
        document_income, source_id = _field_value(fields, "gross_monthly_salary", "monthly_income", "gross_salary")
        if document_income is not None:
            income_comparisons.append(compare_value("Monthly Income", application.monthly_income, document_income, source_id))
        document_name, name_source = _field_value(fields, "employee_name", "account_holder_name", "taxpayer_name", "name")
        if document_name is not None:
            names.append(compare_value("Borrower Name", application.borrower_name, document_name, name_source))
        document_property, property_source = _field_value(fields, "declared_property_value", "property_value")
        if document_property is not None:
            issues.append(compare_value("Property Value", application.property_value, document_property, property_source))
        score, _ = _field_value(fields, "credit_score")
        if credit_score is None and score is not None:
            numeric_score = _numeric_from_any(score)
            credit_score = int(numeric_score) if numeric_score is not None else None

    issues.extend(income_comparisons)
    issues.extend(names)
    issues.extend(policy_issues)
    missing.extend([] if income else ["Monthly gross income"])
    income_status = "Verified Match" if income_comparisons and all(item.status == "Verified Match" for item in income_comparisons) else "Needs Review" if income_comparisons else "Unable to Compare"
    document_status = "Verified Match" if issues and all(item.status in {"Verified Match", "Minor Difference"} for item in issues) else "Needs Review" if issues else "Unable to Compare"
    if credit_score is None:
        missing.append("Credit score (not found in analyzed documents)")
    if MIN_CREDIT_SCORE is not None and credit_score is not None and credit_score < MIN_CREDIT_SCORE:
        issues.append(Comparison("Credit Score", str(MIN_CREDIT_SCORE), str(credit_score), None, None, "Policy Review Required", f"Credit score is below configured demonstration threshold {MIN_CREDIT_SCORE}."))
    status = "Missing Information" if missing and not issues else "Policy Review Required" if any(item.status == "Policy Review Required" for item in issues) else "Needs Review" if any(item.status == "Needs Review" for item in issues) else "Valid"
    return {
        "monthly_income": float(income),
        "monthly_debt": float(debt),
        "loan_amount": float(loan),
        "property_value": float(property_value),
        "dti": float(dti),
        "ltv": float(ltv),
        "credit_score": credit_score,
        "validation_status": status,
        "income_consistency": income_status,
        "document_consistency": document_status,
        "missing_information": missing,
        "issues": issues,
        "calculated_at": datetime.utcnow(),
    }
