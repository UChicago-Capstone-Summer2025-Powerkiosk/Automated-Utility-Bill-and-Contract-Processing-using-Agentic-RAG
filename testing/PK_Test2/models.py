from typing import Literal, Union, List, Dict, Optional
from pydantic import BaseModel, TypeAdapter


from typing import Literal, Any
from pydantic import BaseModel, TypeAdapter


class YearlyUsageBreakdown(BaseModel):
    type: Literal["table", "text", "image"]
    content: Any  # no restrictions


class ServiceEntry(BaseModel):
    account_number: str
    service_reference: Optional[str] = None
    meter_number: str
    usage: float
    unit: str
    service_address: str
    usage_period: str
    delivery_charge: Optional[str] = None
    supply_charge: Optional[str] = None
    tax_charge: Optional[str] = None

    yearly_usage_breakdown: Optional[YearlyUsageBreakdown] = None

    model_config = {"extra": "forbid"}


class PassResponse(BaseModel):
    Pass: Literal["Pass"]


ServiceEntryResponse = Union[ServiceEntry, PassResponse]
adapter_service_entry = TypeAdapter(Dict[str, ServiceEntryResponse])


class StatementDate(BaseModel):
    day: int
    month: int
    year: int


class UtilityBillInfo(BaseModel):
    bill_type: List[str]
    extracting: Literal["electricity", "natural_gas"]
    statement_date: StatementDate
    customer_dba_name: str
    billed_usage: float
    rate_class: Optional[str] = None
    delivery_charge: Optional[str] = None
    supply_charge: Optional[str] = None
    tax_charge: Optional[str] = None

    model_config = {"extra": "forbid"}


UtilityBillResponse = Union[UtilityBillInfo, PassResponse]
adapter_utility_bill = TypeAdapter(UtilityBillResponse)


# ===== Loose fallback models =====


class LooseYearlyUsageBreakdown(BaseModel):
    type: Optional[Literal["table", "text", "image"]] = None
    content: Optional[str] = None

    model_config = {"extra": "ignore"}


class LooseServiceEntry(BaseModel):
    account_number: Optional[str] = None
    service_reference: Optional[str] = None
    meter_number: Optional[str] = None
    usage: Optional[float] = None
    unit: Optional[str] = None
    service_address: Optional[str] = None
    usage_period: Optional[str] = None
    delivery_charge: Optional[str] = None
    supply_charge: Optional[str] = None
    tax_charge: Optional[str] = None

    yearly_usage_breakdown: Optional[LooseYearlyUsageBreakdown] = None

    model_config = {"extra": "ignore"}


LooseServiceEntryResponse = Union[LooseServiceEntry, PassResponse]
adapter_loose_service_entry = TypeAdapter(Dict[str, LooseServiceEntryResponse])


class LooseStatementDate(BaseModel):
    day: Optional[int] = None
    month: Optional[int] = None
    year: Optional[int] = None

    model_config = {"extra": "ignore"}


class LooseUtilityBillInfo(BaseModel):
    bill_type: Optional[List[str]] = None
    extracting: Optional[Literal["electricity", "natural_gas"]] = None
    statement_date: Optional[LooseStatementDate] = None
    customer_dba_name: Optional[str] = None
    billed_usage: Optional[float] = None
    rate_class: Optional[str] = None
    delivery_charge: Optional[str] = None
    supply_charge: Optional[str] = None
    tax_charge: Optional[str] = None
    model_config = {"extra": "ignore"}


LooseUtilityBillResponse = Union[LooseUtilityBillInfo, PassResponse]
adapter_loose_utility_bill = TypeAdapter(LooseUtilityBillResponse)


# md text second check
class LineCorrection(BaseModel):
    original_line: str
    corrected_line: str


adapter_im2txt = TypeAdapter(list[LineCorrection])
loose_adapter_im2txt = TypeAdapter(list[LineCorrection])