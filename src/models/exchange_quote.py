from pydantic import BaseModel, Field


class ExchangeQuote(BaseModel):
    currency_code: str = Field(description="ISO currency code, e.g. USD")
    currency_name: str = Field(description="Currency pair description")
    pair: str = Field(description="Trading pair, e.g. USD-BRL")
    bid: float = Field(ge=0, description="Buy price in BRL")
    ask: float = Field(ge=0, description="Sell price in BRL")
    high: float = Field(ge=0, description="Daily high")
    low: float = Field(ge=0, description="Daily low")
    variation_pct: float = Field(description="Daily variation percentage")
    quoted_at: str = Field(description="Quote timestamp")
