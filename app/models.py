from pydantic import BaseModel, Field, HttpUrl


class WatchItemCreate(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    url: HttpUrl
    retailer: str = Field(pattern="^(target|walmart|topps|other)$")
    max_price: float | None = Field(default=None, gt=0)
    interval_seconds: int = Field(default=90, ge=60, le=3600)


class WatchItemUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=140)
    max_price: float | None = Field(default=None, gt=0)
    interval_seconds: int | None = Field(default=None, ge=60, le=3600)
    enabled: bool | None = None


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict[str, str]
