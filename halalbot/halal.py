"""Halal savdo cheklovlari (Shariah constraints).

Bu modul botning har bir harakatini tekshiradi. Qoidalar:
  1. Faqat SPOT bozor. Futures / perpetual / margin / leverage TAQIQLANADI
     (funding rate = riba, leverage = qarzga savdo, gharar).
  2. Faqat LONG. Short (o'zingda yo'q narsani sotish) TAQIQLANADI.
  3. Sotish faqat hisobda haqiqatan bor miqdorga (naked sell yo'q).
  4. Foizli mahsulotlar yo'q: Earn/Flexible savings/Lending, leverage tokenlar
     (UP/DOWN/BULL/BEAR), lending-protokol tokenlari ro'yxatdan chiqarilgan.
  5. Qarz olish (borrow) API chaqiruvlari umuman yo'q.

Ogohlantirish: bu ro'yxat konservativ texnik filtr, fatvo emas. Qaysi coin
halol ekanini o'z ulamolaringiz bilan tasdiqlang.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ALLOWED_MARKET_TYPES = {"spot"}
FORBIDDEN_MARKET_TYPES = {"futures", "usdm", "coinm", "perpetual", "margin", "isolated_margin", "cross_margin", "options"}

# Leverage tokenlar va foiz/qimor bilan bog'liq tokenlar (konservativ ro'yxat).
BLOCKED_BASE_ASSETS = {
    # Binance leveraged tokens
    "BTCUP", "BTCDOWN", "ETHUP", "ETHDOWN", "BNBUP", "BNBDOWN", "ADAUP", "ADADOWN",
    "LINKUP", "LINKDOWN", "DOTUP", "DOTDOWN", "XRPUP", "XRPDOWN", "SXPUP", "SXPDOWN",
    # Lending / interest protocols
    "AAVE", "COMP", "MKR", "CREAM", "VENUS", "XVS", "JST", "ALPACA", "KAVA",
    # Gambling / casino
    "FUN", "WIN", "DICE",
}

# Kotirovka valyutasi sifatida ruxsat etilgan aktivlar.
ALLOWED_QUOTE_ASSETS = {"USDT", "USDC", "FDUSD", "BTC", "ETH", "BNB", "TRY", "EUR"}

FORBIDDEN_ENDPOINT_FRAGMENTS = (
    "/fapi/", "/dapi/", "/eapi/",           # USD-M futures, COIN-M futures, options
    "/sapi/v1/margin", "/sapi/v1/loan",     # margin, crypto loans
    "/sapi/v1/lending", "/sapi/v1/simple-earn", "/sapi/v1/staking",
    "/sapi/v1/futures", "/sapi/v1/portfolio", "/sapi/v1/bswap",
)


class HalalViolation(Exception):
    """Shariah cheklovini buzadigan harakat urinishi."""


@dataclass
class HalalPolicy:
    market_type: str = "spot"
    leverage: float = 1.0
    allow_short: bool = False
    blocked_base_assets: set = field(default_factory=lambda: set(BLOCKED_BASE_ASSETS))
    allowed_quote_assets: set = field(default_factory=lambda: set(ALLOWED_QUOTE_ASSETS))

    def validate_config(self) -> None:
        mt = self.market_type.lower()
        if mt in FORBIDDEN_MARKET_TYPES or mt not in ALLOWED_MARKET_TYPES:
            raise HalalViolation(f"Bozor turi '{self.market_type}' taqiqlangan: faqat spot ruxsat etiladi")
        if self.leverage != 1.0:
            raise HalalViolation(f"Leverage {self.leverage}x taqiqlangan: faqat 1x (o'z mablag'ing)")
        if self.allow_short:
            raise HalalViolation("Short savdo taqiqlangan: o'zingda yo'q narsani sotib bo'lmaydi")

    def split_symbol(self, symbol: str) -> tuple[str, str]:
        sym = symbol.upper().replace("/", "")
        for q in sorted(self.allowed_quote_assets, key=len, reverse=True):
            if sym.endswith(q) and len(sym) > len(q):
                return sym[: -len(q)], q
        raise HalalViolation(f"'{symbol}' kotirovka valyutasi ruxsat etilganlar ro'yxatida emas")

    def validate_symbol(self, symbol: str) -> None:
        base, _quote = self.split_symbol(symbol)
        if base in self.blocked_base_assets:
            raise HalalViolation(f"'{base}' aktivi bloklangan (leverage token / foiz / qimor)")
        for tag in ("UP", "DOWN", "BULL", "BEAR"):
            if base.endswith(tag) and len(base) > len(tag) + 1:
                raise HalalViolation(f"'{base}' leverage token ko'rinishida — taqiqlangan")

    def validate_order(self, side: str, qty: float, holdings_base: float, holdings_quote: float,
                       price: float) -> None:
        """Buyurtma faqat o'z mablag'i doirasida bo'lishini tekshiradi."""
        side = side.upper()
        if qty <= 0:
            raise HalalViolation("Miqdor musbat bo'lishi kerak")
        if side == "SELL":
            if qty > holdings_base * (1 + 1e-9):
                raise HalalViolation(
                    f"SELL {qty} > hisobda bor {holdings_base}: o'zingda yo'q narsani sotish (short) taqiqlangan")
        elif side == "BUY":
            cost = qty * price
            if cost > holdings_quote * (1 + 1e-9):
                raise HalalViolation(
                    f"BUY {cost:.2f} > mavjud {holdings_quote:.2f}: qarzga/marginga sotib olish taqiqlangan")
        else:
            raise HalalViolation(f"Noma'lum tomon: {side}")

    @staticmethod
    def validate_endpoint(path: str) -> None:
        for frag in FORBIDDEN_ENDPOINT_FRAGMENTS:
            if frag in path:
                raise HalalViolation(f"API yo'li '{path}' taqiqlangan mahsulotga tegishli ({frag})")
