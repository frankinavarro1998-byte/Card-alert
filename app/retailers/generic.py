from __future__ import annotations
import json
import re
import httpx
from bs4 import BeautifulSoup
from .base import CheckResult, RetailerChecker

PRICE_RE = re.compile(r"\$\s*([0-9]{1,5}(?:\.[0-9]{2})?)")


class GenericChecker(RetailerChecker):
    name = "other"
    positive_signals = ("add to cart", "in stock", "available for shipping", "ship it")
    negative_signals = ("out of stock", "sold out", "temporarily out of stock", "currently unavailable")

    async def fetch(self, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 16) AppleWebKit/537.36 Chrome/136 Safari/537.36 CardStockAlert/1.0",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(follow_redirects=True, timeout=15, headers=headers) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    def detect_price(self, html: str) -> float | None:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                data = json.loads(script.string or "{}")
                blobs = data if isinstance(data, list) else [data]
                for blob in blobs:
                    offers = blob.get("offers") if isinstance(blob, dict) else None
                    if isinstance(offers, dict) and offers.get("price") is not None:
                        return float(offers["price"])
            except Exception:
                pass
        match = PRICE_RE.search(soup.get_text(" ", strip=True))
        return float(match.group(1)) if match else None

    def detect_status(self, html: str) -> CheckResult:
        low = html.lower()
        # Prefer structured schema.org inventory data when present.
        if "schema.org/instock" in low or '"availability":"instock"' in low:
            return CheckResult("IN_STOCK", self.detect_price(html), "Structured inventory says InStock")
        if "schema.org/outofstock" in low or '"availability":"outofstock"' in low:
            return CheckResult("OUT_OF_STOCK", self.detect_price(html), "Structured inventory says OutOfStock")

        # Negative signals are checked first to avoid phrases such as "not in stock".
        if any(s in low for s in self.negative_signals):
            return CheckResult("OUT_OF_STOCK", self.detect_price(html), "Retail page shows an unavailable signal")
        if any(s in low for s in self.positive_signals):
            return CheckResult("IN_STOCK", self.detect_price(html), "Retail page shows a purchase/availability signal")
        return CheckResult("UNKNOWN", self.detect_price(html), "No reliable stock signal found")

    async def check(self, url: str) -> CheckResult:
        try:
            html = await self.fetch(url)
            return self.detect_status(html)
        except httpx.HTTPStatusError as e:
            return CheckResult("UNKNOWN", reason=f"HTTP {e.response.status_code}")
        except Exception as e:
            return CheckResult("UNKNOWN", reason=str(e)[:180])
