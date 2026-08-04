"""COMPARE AI — Countries Router"""
from fastapi import APIRouter
router = APIRouter()

COUNTRIES = {
    "BD": {
        "code": "BD",
        "name": "Bangladesh",
        "currency_code": "BDT",
        "currency_symbol": "৳",
        "currency_position": "before",
        "is_live": True,
        "launched_at": "2026-08-04",
        "languages": ["en", "bn"],
        "rtl": False,
        "products_live": ["personal_loan", "home_loan", "savings", "fdr", "dps"],
        "regulator": "Bangladesh Bank",
        "flag_emoji": "🇧🇩",
    },
    "IN": {"code": "IN", "name": "India", "currency_code": "INR", "currency_symbol": "₹", "is_live": False, "flag_emoji": "🇮🇳"},
    "PK": {"code": "PK", "name": "Pakistan", "currency_code": "PKR", "currency_symbol": "Rs", "is_live": False, "flag_emoji": "🇵🇰"},
    "NP": {"code": "NP", "name": "Nepal", "currency_code": "NPR", "currency_symbol": "Rs", "is_live": False, "flag_emoji": "🇳🇵"},
    "LK": {"code": "LK", "name": "Sri Lanka", "currency_code": "LKR", "currency_symbol": "Rs", "is_live": False, "flag_emoji": "🇱🇰"},
    "MY": {"code": "MY", "name": "Malaysia", "currency_code": "MYR", "currency_symbol": "RM", "is_live": False, "flag_emoji": "🇲🇾"},
    "ID": {"code": "ID", "name": "Indonesia", "currency_code": "IDR", "currency_symbol": "Rp", "is_live": False, "flag_emoji": "🇮🇩"},
    "PH": {"code": "PH", "name": "Philippines", "currency_code": "PHP", "currency_symbol": "₱", "is_live": False, "flag_emoji": "🇵🇭"},
    "NG": {"code": "NG", "name": "Nigeria", "currency_code": "NGN", "currency_symbol": "₦", "is_live": False, "flag_emoji": "🇳🇬"},
    "GH": {"code": "GH", "name": "Ghana", "currency_code": "GHS", "currency_symbol": "₵", "is_live": False, "flag_emoji": "🇬🇭"},
    "ZA": {"code": "ZA", "name": "South Africa", "currency_code": "ZAR", "currency_symbol": "R", "is_live": False, "flag_emoji": "🇿🇦"},
    "SA": {"code": "SA", "name": "Saudi Arabia", "currency_code": "SAR", "currency_symbol": "﷼", "is_live": False, "flag_emoji": "🇸🇦"},
    "AE": {"code": "AE", "name": "UAE", "currency_code": "AED", "currency_symbol": "د.إ", "is_live": False, "flag_emoji": "🇦🇪"},
    "EG": {"code": "EG", "name": "Egypt", "currency_code": "EGP", "currency_symbol": "£E", "is_live": False, "flag_emoji": "🇪🇬"},
    "TZ": {"code": "TZ", "name": "Tanzania", "currency_code": "TZS", "currency_symbol": "TSh", "is_live": False, "flag_emoji": "🇹🇿"},
}


@router.get("/")
async def list_countries():
    """List all supported countries."""
    return {"countries": list(COUNTRIES.values()), "live_count": sum(1 for c in COUNTRIES.values() if c.get("is_live"))}


@router.get("/{country_code}")
async def get_country(country_code: str):
    """Get country details."""
    country = COUNTRIES.get(country_code.upper())
    if not country:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Country not found: {country_code}")
    return country


@router.get("/{country_code}/products")
async def list_country_products(country_code: str):
    """List available product types for a country."""
    country = COUNTRIES.get(country_code.upper())
    if not country or not country.get("is_live"):
        return {"products": [], "message": "Country not yet live"}
    return {"country_code": country_code, "products": country.get("products_live", [])}
