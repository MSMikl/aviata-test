from decimal import Decimal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AirportTime(BaseModel):
    at: datetime
    airport: str


class Segment(BaseModel):
    operating_airline: str
    marketing_airline: str
    flight_number: str
    equipment: str | None
    dep: AirportTime
    arr: AirportTime
    baggage: str | None


class Flight(BaseModel):
    duration: int = Field(
        default=0,
        description='Продолжительность полета',
        gt=0,
    )
    segments: list[Segment]


class Currency(Enum):
    EUR = 'EUR'
    RUB = 'RUB'
    USD = 'USD'
    KZT = 'KZT'


class Price(BaseModel):
    dec_amount: float = Field(
        default=None,
        exclude=True,
    )
    amount: str = ''
    currency: Currency | None


class Pricing(BaseModel):
    total: str
    base: str
    taxes: str
    currency: Currency

    def dict(self, *args, **kwargs):
        loaded_dict = super().dict(*args, **kwargs)
        loaded_dict.update(
            currency=loaded_dict['currency'].value,
        )
        return loaded_dict


class Variant(BaseModel):
    flights: list[Flight]
    refundable: bool
    validating_airline: str
    pricing: Pricing
    price: Price = Price(dec_amount=None, amount='', currency=None)


class SearchStatus(Enum):
    PENDING = 'PENDING'
    COMPLETED = 'COMPLETED'


class Search(BaseModel):
    search_id: str = Field(
        alias='_id'
    )
    status: SearchStatus = SearchStatus.PENDING
    items: list[Variant] = []

    def dict(self, *args, **kwargs):
        loaded_dict = super().dict(*args, **kwargs)
        loaded_dict.update(
            status=loaded_dict['status'].value,
        )
        return loaded_dict

    class Config:
        allow_population_by_field_name = True
