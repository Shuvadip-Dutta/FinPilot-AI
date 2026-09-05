from django.db import migrations


def seed_companies(apps, schema_editor):
    Company = apps.get_model("research", "Company")

    seed_data = [
        {
            "ticker": "LT",
            "name": "Larsen & Toubro Ltd",
            "isin": "INE018A01030",
            "exchange": "NSE",
            "country": "India",
            "instrument_key": "NSE_EQ|INE018A01030",
            "sector": "Capital Goods",
            "industry": "Engineering & Construction",
            "provider_symbols": {
                "indianapi": "LARSEN",
                "upstox": "NSE_EQ|INE018A01030",
                "marketaux": "LT.NS",
                "finnhub": "LT",
            },
        },
        {
            "ticker": "RELIANCE",
            "name": "Reliance Industries Ltd",
            "isin": "INE002A01018",
            "exchange": "NSE",
            "country": "India",
            "instrument_key": "NSE_EQ|INE002A01018",
            "sector": "Energy",
            "industry": "Refining & Marketing",
            "provider_symbols": {
                "indianapi": "RELIANCE",
                "upstox": "NSE_EQ|INE002A01018",
                "marketaux": "RELIANCE.NS",
                "finnhub": "RELIANCE",
            },
        },
        {
            "ticker": "TCS",
            "name": "Tata Consultancy Services Ltd",
            "isin": "INE467B01029",
            "exchange": "NSE",
            "country": "India",
            "instrument_key": "NSE_EQ|INE467B01029",
            "sector": "Technology",
            "industry": "IT Services",
            "provider_symbols": {
                "indianapi": "TCS",
                "upstox": "NSE_EQ|INE467B01029",
                "marketaux": "TCS.NS",
                "finnhub": "TCS",
            },
        },
        {
            "ticker": "INFY",
            "name": "Infosys Ltd",
            "isin": "INE009A01021",
            "exchange": "NSE",
            "country": "India",
            "instrument_key": "NSE_EQ|INE009A01021",
            "sector": "Technology",
            "industry": "IT Services",
            "provider_symbols": {
                "indianapi": "INFY",
                "upstox": "NSE_EQ|INE009A01021",
                "marketaux": "INFY.NS",
                "finnhub": "INFY",
            },
        },
    ]

    for data in seed_data:
        Company.objects.update_or_create(
            ticker=data["ticker"],
            exchange=data["exchange"],
            defaults=data,
        )


def remove_seed_companies(apps, schema_editor):
    Company = apps.get_model("research", "Company")
    Company.objects.filter(ticker__in=["LT", "RELIANCE", "TCS", "INFY"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("research", "0004_company_instrument_key_company_provider_symbols"),
    ]

    operations = [
        migrations.RunPython(seed_companies, reverse_code=remove_seed_companies),
    ]
