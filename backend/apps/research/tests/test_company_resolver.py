from django.test import TestCase

from apps.research.services.company_resolver import CanonicalCompanyResolver, CompanyIdentity
from apps.research.services.providers.indian_api import IndianAPIProvider
from apps.research.services.providers.upstox import UpstoxProvider
from apps.research.services.symbols import Market, SymbolResolver


class CanonicalCompanyResolverTestCase(TestCase):

    def setUp(self):
        CanonicalCompanyResolver.clear_cache()

    def test_resolve_lt_by_ticker(self):
        identity = CanonicalCompanyResolver.resolve("LT", Market.INDIA)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.ticker, "LT")
        self.assertEqual(identity.legal_name, "Larsen & Toubro Ltd")
        self.assertEqual(identity.isin, "INE018A01030")
        self.assertEqual(identity.instrument_key, "NSE_EQ|INE018A01030")
        self.assertEqual(identity.get_provider_symbol("indianapi"), "LARSEN")
        self.assertEqual(identity.get_provider_symbol("upstox"), "NSE_EQ|INE018A01030")
        self.assertEqual(identity.get_provider_symbol("marketaux"), "LT.NS")

    def test_resolve_by_isin(self):
        identity = CanonicalCompanyResolver.resolve("INE018A01030", Market.INDIA)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.ticker, "LT")
        self.assertEqual(identity.legal_name, "Larsen & Toubro Ltd")

    def test_resolve_by_legal_name(self):
        identity = CanonicalCompanyResolver.resolve("Larsen & Toubro Ltd", Market.INDIA)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.ticker, "LT")

    def test_unseeded_ticker_fallback(self):
        identity = CanonicalCompanyResolver.resolve("ABCDEF", Market.INDIA)
        self.assertIsNotNone(identity)
        self.assertEqual(identity.ticker, "ABCDEF")
        self.assertEqual(identity.get_provider_symbol("marketaux"), "ABCDEF.NS")
        self.assertEqual(identity.get_provider_symbol("unknown_provider"), "ABCDEF")

    def test_symbol_resolver_delegation(self):
        resolved = SymbolResolver.resolve("LT", Market.INDIA, provider="indianapi")
        self.assertEqual(resolved, "LARSEN")

    def test_indian_api_lt_mapping(self):
        provider = IndianAPIProvider.__new__(IndianAPIProvider)
        provider.SYMBOL_ALIASES = {"LT": "LARSEN"}
        resolved = provider._resolve_provider_symbol("LT")
        self.assertEqual(resolved, "LARSEN")

    def test_upstox_lt_instrument_key_resolution(self):
        provider = UpstoxProvider.__new__(UpstoxProvider)
        key = provider._resolve_instrument_key("LT")
        self.assertEqual(key, "NSE_EQ|INE018A01030")
