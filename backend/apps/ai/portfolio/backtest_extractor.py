"""Deterministic, bounded parameter extraction for natural language backtest requests.

Parses user messages into typed configuration for PortfolioBacktestInput without LLM math.
"""

import calendar
import re
from datetime import date, datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, ValidationError as PydanticValidationError, model_validator

from apps.portfolio.backtest_builder import INDEX_INSTRUMENT_MAP


class BacktestExtractionError(ValueError):
    """Raised when user explicitly provides invalid or conflicting backtest parameters."""


CANONICAL_BENCHMARK_ALIASES: dict[str, str] = {
    "NIFTY 50": "NIFTY 50",
    "NIFTY50": "NIFTY 50",
    "NIFTY": "NIFTY 50",
    "^NSEI": "NIFTY 50",
    "NIFTY 500": "NIFTY 500",
    "NIFTY500": "NIFTY 500",
    "BANKNIFTY": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "SENSEX": "SENSEX",
    "^BSESN": "SENSEX",
}

MONTH_NAME_TO_NUMBER: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

WORD_TO_NUMBER: dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}


class ExtractedBacktestConfig(BaseModel):
    """Normalized parameters extracted from natural language backtest requests."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    benchmark_ticker: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    initial_capital: float | None = None
    rebalance_frequency: Literal["monthly", "quarterly", "annually", "periodic"] | None = None
    in_sample_window_days: int | None = None
    out_of_sample_step_days: int | None = None
    transaction_cost_bps: float | None = None
    risk_free_rate: float | None = None
    min_weight: float | None = None
    max_weight: float | None = None

    def __init__(self, **data: Any):
        try:
            super().__init__(**data)
        except PydanticValidationError as exc:
            for err in exc.errors():
                ctx_err = err.get("ctx", {}).get("error")
                if isinstance(ctx_err, BacktestExtractionError):
                    raise ctx_err
            raise BacktestExtractionError(str(exc))

    @model_validator(mode="after")
    def validate_extracted_bounds(self) -> "ExtractedBacktestConfig":
        if self.initial_capital is not None and self.initial_capital <= 0:
            raise BacktestExtractionError(
                f"Initial capital must be strictly positive, got {self.initial_capital}."
            )

        if self.transaction_cost_bps is not None and self.transaction_cost_bps < 0:
            raise BacktestExtractionError(
                f"Transaction cost cannot be negative, got {self.transaction_cost_bps}."
            )

        if self.risk_free_rate is not None and self.risk_free_rate < 0:
            raise BacktestExtractionError(
                f"Risk-free rate cannot be negative, got {self.risk_free_rate}."
            )

        if self.min_weight is not None and not (0.0 <= self.min_weight <= 1.0):
            raise BacktestExtractionError(
                f"Minimum weight must be between 0.0 and 1.0, got {self.min_weight}."
            )

        if self.max_weight is not None and not (0.0 <= self.max_weight <= 1.0):
            raise BacktestExtractionError(
                f"Maximum weight must be between 0.0 and 1.0, got {self.max_weight}."
            )

        if (
            self.min_weight is not None
            and self.max_weight is not None
            and self.min_weight > self.max_weight
        ):
            raise BacktestExtractionError(
                f"Minimum weight ({self.min_weight}) cannot exceed maximum weight ({self.max_weight})."
            )

        if self.in_sample_window_days is not None and self.in_sample_window_days < 3:
            raise BacktestExtractionError(
                f"In-sample window days must be at least 3, got {self.in_sample_window_days}."
            )

        if self.out_of_sample_step_days is not None and self.out_of_sample_step_days < 1:
            raise BacktestExtractionError(
                f"Out-of-sample step days must be at least 1, got {self.out_of_sample_step_days}."
            )

        d_from: date | None = None
        d_to: date | None = None

        if self.from_date is not None:
            try:
                d_from = datetime.strptime(self.from_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise BacktestExtractionError(
                    f"Invalid calendar from_date '{self.from_date}': must be a valid YYYY-MM-DD calendar date."
                ) from exc

        if self.to_date is not None:
            try:
                d_to = datetime.strptime(self.to_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise BacktestExtractionError(
                    f"Invalid calendar to_date '{self.to_date}': must be a valid YYYY-MM-DD calendar date."
                ) from exc

        if d_from is not None and d_to is not None:
            if d_from > d_to:
                raise BacktestExtractionError(
                    f"Start date ({self.from_date}) cannot be after end date ({self.to_date})."
                )

        return self

    def to_workflow_kwargs(self) -> dict[str, Any]:
        """Return non-None parameters mapped to PortfolioWorkflowInput fields."""
        mapping = {
            "benchmark_ticker": "backtest_benchmark_ticker",
            "from_date": "backtest_from_date",
            "to_date": "backtest_to_date",
            "initial_capital": "backtest_initial_capital",
            "rebalance_frequency": "backtest_rebalance_frequency",
            "in_sample_window_days": "backtest_in_sample_window_days",
            "out_of_sample_step_days": "backtest_out_of_sample_step_days",
            "transaction_cost_bps": "backtest_transaction_cost_bps",
            "risk_free_rate": "backtest_risk_free_rate",
            "min_weight": "backtest_min_weight",
            "max_weight": "backtest_max_weight",
        }
        res: dict[str, Any] = {}
        for src_k, target_k in mapping.items():
            val = getattr(self, src_k)
            if val is not None:
                res[target_k] = val
        return res


class BacktestParameterExtractor:
    """Extracts bounded backtest configuration from natural-language requests."""

    @classmethod
    def extract(
        cls,
        message: str,
        reference_date: date | datetime | None = None,
    ) -> ExtractedBacktestConfig:
        """Extract and normalize backtest parameters from a user prompt."""
        if reference_date is None:
            ref_d = datetime.now(timezone.utc).date()
        elif isinstance(reference_date, datetime):
            ref_d = reference_date.date()
        else:
            ref_d = reference_date

        benchmark = cls._extract_benchmark(message)
        from_d, to_d = cls._extract_dates(message, ref_d)
        capital = cls._extract_capital(message)
        rebal = cls._extract_rebalance_frequency(message)
        numerics = cls._extract_numerical_parameters(message)

        return ExtractedBacktestConfig(
            benchmark_ticker=benchmark,
            from_date=from_d,
            to_date=to_d,
            initial_capital=capital,
            rebalance_frequency=rebal,
            in_sample_window_days=numerics.get("in_sample_window_days"),
            out_of_sample_step_days=numerics.get("out_of_sample_step_days"),
            transaction_cost_bps=numerics.get("transaction_cost_bps"),
            risk_free_rate=numerics.get("risk_free_rate"),
            min_weight=numerics.get("min_weight"),
            max_weight=numerics.get("max_weight"),
        )

    @classmethod
    def _resolve_benchmark_candidate(cls, candidate: str) -> str | None:
        """Resolve raw extracted candidate string to canonical benchmark ticker if recognized."""
        if not candidate:
            return None

        # Exact match in canonical aliases
        if candidate in CANONICAL_BENCHMARK_ALIASES:
            return CANONICAL_BENCHMARK_ALIASES[candidate]

        # Alias substring match (longest alias first)
        for alias, canonical in sorted(
            CANONICAL_BENCHMARK_ALIASES.items(), key=lambda x: -len(x[0])
        ):
            if re.search(r"(?:^|\s|\b)" + re.escape(alias) + r"(?:\b|\s|$)", candidate, re.IGNORECASE):
                return canonical

        # Direct match in INDEX_INSTRUMENT_MAP
        if candidate in INDEX_INSTRUMENT_MAP:
            return candidate

        return None

    @classmethod
    def _extract_benchmark(cls, message: str) -> str | None:
        """Extract benchmark index identifier when explicit benchmark/comparison intent is present."""
        # 1. Prefix pattern where comparison/benchmark intent precedes candidate
        # e.g.: against, versus, vs, compare with/to, compared with/to, benchmark is, benchmark:
        prefix_pattern = (
            r"(?:\b(?:against|versus|vs\.?|compare\s+(?:with|to)|compared\s+(?:with|to)|"
            r"benchmarked\s+against|benchmark(?:\s*:|\s+is|\s*=|\s+as|\b))\s*)"
            r"([A-Za-z0-9_\^ ]+?)(?=[,\.;]|\s+(?:for|with|from|over|using|in|starting|start|rebalanc)|\s*$)"
        )

        for match in re.finditer(prefix_pattern, message, re.IGNORECASE):
            preceding = message[:match.start()]
            # If the comparison prefix is negated, do not extract this candidate
            if re.search(
                r"\b(?:don'?t|dont|do\s+not|not|never|without|no)\b(?:\s+\w+){0,3}\s*$",
                preceding,
                re.IGNORECASE,
            ):
                continue

            candidate = match.group(1).strip().upper()
            resolved = cls._resolve_benchmark_candidate(candidate)
            if resolved:
                return resolved

        # 2. Reverse pattern: "[candidate] as [a/the] benchmark"
        reverse_pattern = (
            r"\b([A-Za-z0-9_\^ ]+?)\s+as\s+(?:a\s+|the\s+)?benchmark\b"
        )
        for match in re.finditer(reverse_pattern, message, re.IGNORECASE):
            preceding = message[:match.start()]
            if re.search(
                r"\b(?:don'?t|dont|do\s+not|not|never|without|no)\b(?:\s+\w+){0,3}\s*$",
                preceding,
                re.IGNORECASE,
            ):
                continue

            candidate = match.group(1).strip().upper()
            resolved = cls._resolve_benchmark_candidate(candidate)
            if resolved:
                return resolved

        return None

    @classmethod
    def _extract_dates(
        cls,
        message: str,
        reference_date: date,
    ) -> tuple[str | None, str | None]:
        """Extract explicit or relative date ranges, resolving them deterministically."""
        # Validate explicit calendar dates (YYYY-MM-DD)
        for candidate_iso in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", message):
            try:
                datetime.strptime(candidate_iso, "%Y-%m-%d")
            except ValueError as exc:
                raise BacktestExtractionError(
                    f"Invalid calendar date '{candidate_iso}': must be a valid YYYY-MM-DD calendar date."
                ) from exc

        # 1. Explicit ISO date range (e.g., 2024-01-01 to 2025-12-31)
        iso_matches = re.findall(
            r"\b(\d{4}-\d{2}-\d{2})\s*(?:to|until|through|and|-)\s*(\d{4}-\d{2}-\d{2})\b",
            message,
            re.IGNORECASE,
        )
        if len(iso_matches) > 1:
            distinct_iso = set(iso_matches)
            if len(distinct_iso) > 1:
                raise BacktestExtractionError("Conflicting explicit date ranges detected.")
        if len(iso_matches) == 1:
            return iso_matches[0][0], iso_matches[0][1]

        # 2. Explicit Month Year to Month Year range (e.g., January 2024 to December 2025)
        m_pattern = (
            r"\b(?:from|between)?\s*([a-zA-Z]+)\s+(\d{4})\s*(?:to|until|through|and|-)\s*([a-zA-Z]+)\s+(\d{4})\b"
        )
        m_matches = re.findall(m_pattern, message, re.IGNORECASE)
        valid_m_ranges = []
        for m1, y1, m2, y2 in m_matches:
            m1_l, m2_l = m1.lower(), m2.lower()
            if m1_l in MONTH_NAME_TO_NUMBER and m2_l in MONTH_NAME_TO_NUMBER:
                start_month = MONTH_NAME_TO_NUMBER[m1_l]
                end_month = MONTH_NAME_TO_NUMBER[m2_l]
                from_d = f"{int(y1):04d}-{start_month:02d}-01"
                last_day = calendar.monthrange(int(y2), end_month)[1]
                to_d = f"{int(y2):04d}-{end_month:02d}-{last_day:02d}"
                valid_m_ranges.append((from_d, to_d))

        if len(valid_m_ranges) > 1:
            if len(set(valid_m_ranges)) > 1:
                raise BacktestExtractionError("Conflicting explicit month-year ranges detected.")
        if len(valid_m_ranges) == 1:
            return valid_m_ranges[0]

        # 3. Explicit Year to Year (e.g., from 2022 to 2024)
        y_pattern = r"\b(?:from|between)\s+(\d{4})\s*(?:to|until|through|and|-)\s*(\d{4})\b"
        y_matches = re.findall(y_pattern, message, re.IGNORECASE)
        if len(y_matches) == 1:
            y1, y2 = int(y_matches[0][0]), int(y_matches[0][1])
            return f"{y1:04d}-01-01", f"{y2:04d}-12-31"

        # 4. Relative period (e.g. "last 2 years", "past 1 year", "last 6 months")
        rel_pattern = (
            r"\b(?:last|past|previous)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
            r"(year|years|month|months)\b"
        )
        rel_matches = re.findall(rel_pattern, message, re.IGNORECASE)
        if len(rel_matches) > 1:
            distinct_rel = {
                (WORD_TO_NUMBER.get(m[0].lower(), m[0]), m[1].lower().rstrip("s"))
                for m in rel_matches
            }
            if len(distinct_rel) > 1:
                raise BacktestExtractionError("Conflicting relative time periods detected.")

        if len(rel_matches) >= 1:
            val_str = rel_matches[0][0].lower()
            n = WORD_TO_NUMBER.get(val_str) or int(val_str)
            unit = rel_matches[0][1].lower()
            to_date_str = reference_date.strftime("%Y-%m-%d")

            if "year" in unit:
                target_year = reference_date.year - n
                max_day = calendar.monthrange(target_year, reference_date.month)[1]
                from_date_obj = date(target_year, reference_date.month, min(reference_date.day, max_day))
                return from_date_obj.strftime("%Y-%m-%d"), to_date_str
            elif "month" in unit:
                total_months = reference_date.year * 12 + reference_date.month - 1 - n
                target_year = total_months // 12
                target_month = total_months % 12 + 1
                max_day = calendar.monthrange(target_year, target_month)[1]
                from_date_obj = date(target_year, target_month, min(reference_date.day, max_day))
                return from_date_obj.strftime("%Y-%m-%d"), to_date_str

        return None, None

    @classmethod
    def _extract_capital(cls, message: str) -> float | None:
        """Extract initial starting capital from user message."""
        pattern = (
            r"(?:initial\s+capital|starting\s+capital|start\s+with|starting\s+with|capital(?:\s+of)?|\bwith)\s*"
            r"([+-]?\s*[$₹€]?\s*\d+(?:,\d+)*(?:\.\d+)?)\s*"
            r"(k|lakh|lakhs|lac|lacs|m|million|cr|crore|crores)?\b"
        )
        for match in re.finditer(pattern, message, re.IGNORECASE):
            after_pos = match.end()
            remainder = message[after_pos:].lstrip()
            # If immediately followed by %, bps, day, month, year, weight, cost, rate, fee - skip!
            if re.match(
                r"^(?:%|bps|day|days|month|months|year|years|weight|cost|fee|rate)",
                remainder,
                re.IGNORECASE,
            ):
                continue

            raw_str = (
                match.group(1)
                .replace(",", "")
                .replace("$", "")
                .replace("₹", "")
                .replace("€", "")
                .replace(" ", "")
            )
            try:
                val = float(raw_str)
            except ValueError:
                continue

            unit = (match.group(2) or "").lower()
            if unit == "k":
                val *= 1000.0
            elif unit in ("lakh", "lakhs", "lac", "lacs"):
                val *= 100000.0
            elif unit in ("m", "million"):
                val *= 1000000.0
            elif unit in ("cr", "crore", "crores"):
                val *= 10000000.0

            if val <= 0:
                raise BacktestExtractionError(f"Initial capital must be strictly positive, got {val}.")

            return val

        return None

    @classmethod
    def _extract_rebalance_frequency(
        cls, message: str
    ) -> Literal["monthly", "quarterly", "annually", "periodic"] | None:
        """Extract explicit rebalance frequency."""
        pattern = r"\b(monthly|quarterly|annually|yearly|periodic)\b"
        match = re.search(pattern, message, re.IGNORECASE)
        if not match:
            return None

        freq = match.group(1).lower()
        if freq == "yearly":
            return "annually"
        if freq in ("monthly", "quarterly", "annually", "periodic"):
            return freq  # type: ignore[return-value]
        return None

    @classmethod
    def _extract_numerical_parameters(cls, message: str) -> dict[str, Any]:
        """Extract transaction cost, risk-free rate, weights, and window/step sizes."""
        result: dict[str, Any] = {}

        # 1. Transaction cost
        # e.g., "10 bps", "-5 bps", "0.1% transaction cost"
        tc_bps_m = re.search(r"([+-]?\d+(?:\.\d+)?)\s*bps(?:\s+transaction\s+cost)?\b", message, re.IGNORECASE)
        if tc_bps_m:
            val = float(tc_bps_m.group(1))
            if val < 0:
                raise BacktestExtractionError(f"Transaction cost cannot be negative, got {val}.")
            result["transaction_cost_bps"] = val
        else:
            tc_pct_m = re.search(
                r"([+-]?\d+(?:\.\d+)?)\s*%\s*(?:transaction\s+cost|trading\s+cost|transaction\s+fee|cost)\b",
                message,
                re.IGNORECASE,
            )
            if tc_pct_m:
                val = float(tc_pct_m.group(1)) * 100.0
                if val < 0:
                    raise BacktestExtractionError(f"Transaction cost cannot be negative, got {val}.")
                result["transaction_cost_bps"] = val
            else:
                tc_prefix_m = re.search(
                    r"transaction\s+cost\s*(?:of\s*)?([+-]?\d+(?:\.\d+)?)\s*(bps|%)?\b",
                    message,
                    re.IGNORECASE,
                )
                if tc_prefix_m:
                    val = float(tc_prefix_m.group(1))
                    unit = (tc_prefix_m.group(2) or "").lower()
                    if unit == "%":
                        val *= 100.0
                    if val < 0:
                        raise BacktestExtractionError(f"Transaction cost cannot be negative, got {val}.")
                    result["transaction_cost_bps"] = val

        # 2. Risk-free rate
        # e.g., "risk free rate 6.5%", "rf 0.05"
        rf_m = re.search(
            r"(?:risk[- ]free\s+rate|rf)\s*(?:of\s*|is\s*|=)?\s*([+-]?\d+(?:\.\d+)?)\s*(%)?",
            message,
            re.IGNORECASE,
        )
        if rf_m:
            val = float(rf_m.group(1))
            if rf_m.group(2) or val > 1.0:
                val /= 100.0
            if val < 0:
                raise BacktestExtractionError(f"Risk-free rate cannot be negative, got {val}.")
            result["risk_free_rate"] = val

        # 3. Minimum weight
        # e.g., "minimum weight 10%", "min weight 0.1"
        min_w_m = re.search(
            r"(?:minimum|min)\s+weight\s*(?:of\s*|is\s*|=)?\s*([+-]?\d+(?:\.\d+)?)\s*(%)?",
            message,
            re.IGNORECASE,
        )
        if min_w_m:
            val = float(min_w_m.group(1))
            if min_w_m.group(2) or val > 1.0:
                val /= 100.0
            if not (0.0 <= val <= 1.0):
                raise BacktestExtractionError(f"Minimum weight must be between 0.0 and 1.0, got {val}.")
            result["min_weight"] = val

        # 4. Maximum weight
        # e.g., "maximum weight 70%", "max weight 0.7"
        max_w_m = re.search(
            r"(?:maximum|max)\s+weight\s*(?:of\s*|is\s*|=)?\s*([+-]?\d+(?:\.\d+)?)\s*(%)?",
            message,
            re.IGNORECASE,
        )
        if max_w_m:
            val = float(max_w_m.group(1))
            if max_w_m.group(2) or val > 1.0:
                val /= 100.0
            if not (0.0 <= val <= 1.0):
                raise BacktestExtractionError(f"Maximum weight must be between 0.0 and 1.0, got {val}.")
            result["max_weight"] = val

        # Validate min_weight <= max_weight if both present
        if (
            "min_weight" in result
            and "max_weight" in result
            and result["min_weight"] > result["max_weight"]
        ):
            raise BacktestExtractionError(
                f"Minimum weight ({result['min_weight']}) cannot exceed maximum weight ({result['max_weight']})."
            )

        # 5. In-sample window days
        # e.g., "252 day window", "in-sample window of 126"
        win_m = re.search(
            r"(\d+)\s*[- ]day\s*(?:in[- ]sample\s+)?window\b|(?:in[- ]sample\s+window)\s*(?:of\s*)?(\d+)",
            message,
            re.IGNORECASE,
        )
        if win_m:
            days = int(win_m.group(1) or win_m.group(2))
            if days < 3:
                raise BacktestExtractionError(f"In-sample window days must be at least 3, got {days}.")
            result["in_sample_window_days"] = days

        # 6. Out-of-sample step days
        # e.g., "21 day step", "out-of-sample step of 63"
        step_m = re.search(
            r"(\d+)\s*[- ]day\s*(?:out[- ]of[- ]sample\s+)?step\b|(?:out[- ]of[- ]sample\s+step)\s*(?:of\s*)?(\d+)",
            message,
            re.IGNORECASE,
        )
        if step_m:
            days = int(step_m.group(1) or step_m.group(2))
            if days < 1:
                raise BacktestExtractionError(f"Out-of-sample step days must be at least 1, got {days}.")
            result["out_of_sample_step_days"] = days

        return result


def extract_backtest_config(
    message: str,
    reference_date: date | datetime | None = None,
) -> ExtractedBacktestConfig:
    """Convenience functional wrapper around BacktestParameterExtractor.extract."""
    return BacktestParameterExtractor.extract(message, reference_date=reference_date)
