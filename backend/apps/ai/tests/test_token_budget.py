from datetime import datetime, timezone
import threading
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.ai.services.token_budget import (
    DegradationTier,
    LLMUsage,
    TokenBudgetCheck,
    TokenBudgetExceededError,
    TokenBudgetManager,
    TPDLimitExceededError,
    TPMLimitExceededError,
    get_default_token_budget_manager,
)


class TokenBudgetManagerTestCase(SimpleTestCase):

    def test_constructor_defaults_and_custom_limits(self):
        manager = TokenBudgetManager()
        self.assertEqual(manager.max_request_tokens, 32768)
        self.assertEqual(manager.safety_reserve_tokens, 1024)
        self.assertEqual(manager.effective_limit, 31744)
        self.assertIsNone(manager.tpm_limit)
        self.assertIsNone(manager.tpd_limit)

        custom = TokenBudgetManager(
            max_request_tokens=1000,
            safety_reserve_tokens=200,
            token_estimation_chars_per_token=4.0,
            tpm_limit=5000,
            tpd_limit=50000,
        )
        self.assertEqual(custom.max_request_tokens, 1000)
        self.assertEqual(custom.safety_reserve_tokens, 200)
        self.assertEqual(custom.effective_limit, 800)
        self.assertEqual(custom.tpm_limit, 5000)
        self.assertEqual(custom.tpd_limit, 50000)

    def test_constructor_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            TokenBudgetManager(max_request_tokens=0)
        with self.assertRaises(ValueError):
            TokenBudgetManager(max_request_tokens=-100)
        with self.assertRaises(ValueError):
            TokenBudgetManager(safety_reserve_tokens=-1)
        with self.assertRaises(ValueError):
            TokenBudgetManager(
                max_request_tokens=1000, safety_reserve_tokens=1000
            )
        with self.assertRaises(ValueError):
            TokenBudgetManager(
                max_request_tokens=1000, safety_reserve_tokens=1200
            )
        with self.assertRaises(ValueError):
            TokenBudgetManager(token_estimation_chars_per_token=0)
        with self.assertRaises(ValueError):
            TokenBudgetManager(token_estimation_chars_per_token=-2.0)
        with self.assertRaises(ValueError):
            TokenBudgetManager(tpm_limit=0)
        with self.assertRaises(ValueError):
            TokenBudgetManager(tpd_limit=-100)

    def test_tpm_and_tpd_disabled_by_default(self):
        manager = TokenBudgetManager()
        snapshot = manager.get_usage_snapshot()
        self.assertEqual(snapshot["current_tpm_usage"], 0)
        self.assertIsNone(snapshot["tpm_limit"])
        self.assertIsNone(snapshot["remaining_tpm"])
        self.assertEqual(snapshot["current_tpd_usage"], 0)
        self.assertIsNone(snapshot["tpd_limit"])
        self.assertIsNone(snapshot["remaining_tpd"])

    def test_request_allowed_and_rejected_under_tpm(self):
        manager = TokenBudgetManager(
            max_request_tokens=10000,
            safety_reserve_tokens=1000,
            tpm_limit=2000,
        )
        messages = [{"role": "user", "content": "Hi"}]

        # Input + output = ~10 + 1500 = 1510 <= 2000 TPM limit -> Allowed
        check = manager.check_request_budget(
            messages=messages, max_output_tokens=1500
        )
        self.assertTrue(check.allowed)

        # Record actual usage of 1500 tokens
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=500,
                completion_tokens=1000,
                total_tokens=1500,
                model="qwen/qwen3.6-27b",
            )
        )

        # Remaining TPM = 2000 - 1500 = 500. Request of output=600 total ~610 > 500 -> Rejected
        with self.assertRaises(TPMLimitExceededError) as ctx:
            manager.validate_request_budget(
                messages=messages, max_output_tokens=600
            )

        exc = ctx.exception
        self.assertEqual(exc.tpm_limit, 2000)
        self.assertEqual(exc.current_tpm_usage, 1500)
        self.assertEqual(exc.remaining_tpm, 500)
        self.assertIn("exceeds remaining TPM quota", str(exc))

    def test_old_tpm_entries_expire_after_60_seconds(self):
        manager = TokenBudgetManager(
            max_request_tokens=10000,
            safety_reserve_tokens=1000,
            tpm_limit=2000,
        )

        start_time = 1000.0
        with patch.object(manager, "_now_ts", return_value=start_time):
            manager.record_actual_usage(
                LLMUsage(
                    prompt_tokens=500,
                    completion_tokens=1000,
                    total_tokens=1500,
                    model="qwen/qwen3.6-27b",
                )
            )
            snapshot_at_start = manager.get_usage_snapshot()
            self.assertEqual(snapshot_at_start["current_tpm_usage"], 1500)

        # Advance time by 61 seconds
        with patch.object(manager, "_now_ts", return_value=start_time + 61.0):
            snapshot_after_61s = manager.get_usage_snapshot()
            self.assertEqual(snapshot_after_61s["current_tpm_usage"], 0)
            self.assertEqual(snapshot_after_61s["remaining_tpm"], 2000)

    def test_request_allowed_and_rejected_under_tpd(self):
        manager = TokenBudgetManager(
            max_request_tokens=10000,
            safety_reserve_tokens=1000,
            tpd_limit=5000,
        )
        messages = [{"role": "user", "content": "Hi"}]

        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=2000,
                completion_tokens=2500,
                total_tokens=4500,
                model="qwen/qwen3.6-27b",
            )
        )

        # Current TPD usage = 4500, remaining = 500. Request of output=600 total ~610 > 500 -> Rejected
        with self.assertRaises(TPDLimitExceededError) as ctx:
            manager.validate_request_budget(
                messages=messages, max_output_tokens=600
            )

        exc = ctx.exception
        self.assertEqual(exc.tpd_limit, 5000)
        self.assertEqual(exc.current_tpd_usage, 4500)
        self.assertEqual(exc.remaining_tpd, 500)
        self.assertIn("exceeds remaining TPD quota", str(exc))

    def test_tpd_resets_on_utc_date_change(self):
        manager = TokenBudgetManager(
            max_request_tokens=10000,
            safety_reserve_tokens=1000,
            tpd_limit=5000,
        )

        day1 = datetime(2026, 9, 4, 23, 59, 0, tzinfo=timezone.utc)
        day2 = datetime(2026, 9, 5, 0, 1, 0, tzinfo=timezone.utc)

        with patch.object(manager, "_now_dt", return_value=day1):
            manager.record_actual_usage(
                LLMUsage(
                    prompt_tokens=2000,
                    completion_tokens=2500,
                    total_tokens=4500,
                    model="qwen/qwen3.6-27b",
                )
            )
            snapshot_day1 = manager.get_usage_snapshot()
            self.assertEqual(snapshot_day1["current_tpd_usage"], 4500)

        with patch.object(manager, "_now_dt", return_value=day2):
            snapshot_day2 = manager.get_usage_snapshot()
            self.assertEqual(snapshot_day2["current_tpd_usage"], 0)
            self.assertEqual(snapshot_day2["remaining_tpd"], 5000)

    def test_usage_snapshot_values(self):
        manager = TokenBudgetManager(
            max_request_tokens=10000,
            safety_reserve_tokens=1000,
            tpm_limit=2000,
            tpd_limit=10000,
        )

        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=100,
                completion_tokens=200,
                total_tokens=300,
                model="qwen/qwen3.6-27b",
            )
        )

        snapshot = manager.get_usage_snapshot()
        self.assertEqual(snapshot["current_tpm_usage"], 300)
        self.assertEqual(snapshot["tpm_limit"], 2000)
        self.assertEqual(snapshot["remaining_tpm"], 1700)
        self.assertEqual(snapshot["current_tpd_usage"], 300)
        self.assertEqual(snapshot["tpd_limit"], 10000)
        self.assertEqual(snapshot["remaining_tpd"], 9700)

    def test_thread_safe_accounting(self):
        manager = TokenBudgetManager(tpm_limit=100000, tpd_limit=100000)

        def worker():
            for _ in range(50):
                manager.record_actual_usage(
                    LLMUsage(
                        prompt_tokens=1,
                        completion_tokens=1,
                        total_tokens=2,
                        model="test",
                    )
                )

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        snapshot = manager.get_usage_snapshot()
        self.assertEqual(snapshot["current_tpm_usage"], 1000)
        self.assertEqual(snapshot["current_tpd_usage"], 1000)

    def test_llm_usage_structure_validation(self):
        usage = LLMUsage(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model="qwen/qwen3.6-27b",
        )
        self.assertEqual(usage.prompt_tokens, 10)
        self.assertEqual(usage.completion_tokens, 20)
        self.assertEqual(usage.total_tokens, 30)
        self.assertEqual(usage.model, "qwen/qwen3.6-27b")

        with self.assertRaises(ValueError):
            LLMUsage(
                prompt_tokens=-1,
                completion_tokens=5,
                total_tokens=4,
                model="model",
            )

    def test_empty_messages_handled_correctly(self):
        manager = TokenBudgetManager(
            max_request_tokens=1000, safety_reserve_tokens=100
        )
        input_tokens = manager.estimate_input_tokens([])
        self.assertEqual(input_tokens, 0)

        check = manager.check_request_budget(
            messages=[], max_output_tokens=100
        )
        self.assertEqual(check.estimated_input_tokens, 0)
        self.assertEqual(check.requested_output_tokens, 100)
        self.assertEqual(check.estimated_total_tokens, 100)
        self.assertTrue(check.allowed)
        self.assertEqual(check.remaining_budget, 800)

    def test_small_request_allowed(self):
        manager = TokenBudgetManager(
            max_request_tokens=1000, safety_reserve_tokens=100
        )
        messages = [{"role": "user", "content": "Hello world"}]
        check = manager.check_request_budget(
            messages=messages, max_output_tokens=50
        )

        self.assertTrue(check.allowed)
        self.assertGreater(check.remaining_budget, 0)

    def test_request_above_effective_limit_rejected(self):
        manager = TokenBudgetManager(
            max_request_tokens=1000, safety_reserve_tokens=100
        )
        messages = [{"role": "user", "content": "Hello"}]
        input_tokens = manager.estimate_input_tokens(messages)
        output_tokens = (manager.effective_limit - input_tokens) + 1

        with self.assertRaises(TokenBudgetExceededError) as ctx:
            manager.validate_request_budget(
                messages=messages, max_output_tokens=output_tokens
            )

        exc = ctx.exception
        self.assertEqual(exc.max_request_tokens, 1000)
        self.assertEqual(exc.safety_reserve_tokens, 100)
        self.assertEqual(exc.effective_limit, 900)

    def test_get_default_token_budget_manager_returns_singleton(self):
        m1 = get_default_token_budget_manager()
        m2 = get_default_token_budget_manager()
        self.assertIs(m1, m2)
        self.assertIsInstance(m1, TokenBudgetManager)

    def test_get_default_token_budget_manager_uses_settings(self):
        with patch("apps.ai.services.token_budget._default_manager", None):
            with patch("django.conf.settings.GROQ_TPM_LIMIT", 50000), patch(
                "django.conf.settings.GROQ_TPD_LIMIT", 500000
            ), patch(
                "django.conf.settings.GROQ_MAX_REQUEST_TOKENS", 16384
            ), patch(
                "django.conf.settings.GROQ_SAFETY_RESERVE_TOKENS", 512
            ):
                manager = get_default_token_budget_manager()
                self.assertEqual(manager.tpm_limit, 50000)
                self.assertEqual(manager.tpd_limit, 500000)
                self.assertEqual(manager.max_request_tokens, 16384)
                self.assertEqual(manager.safety_reserve_tokens, 512)

    def test_degradation_tier_no_quotas_configured_returns_normal(self):
        manager = TokenBudgetManager()
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.NORMAL)
        check = manager.check_request_budget(
            messages=[{"role": "user", "content": "Hello"}],
            max_output_tokens=100,
        )
        self.assertEqual(check.degradation_tier, DegradationTier.NORMAL)

    def test_degradation_tier_thresholds_for_tpm_quota(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
        )

        # Usage 6000 -> remaining 4000 (40%) -> NORMAL
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=3000,
                completion_tokens=3000,
                total_tokens=6000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.NORMAL)

        # Usage 1000 more (total 7000) -> remaining 3000 (30%) -> CONSTRAINED
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=500,
                completion_tokens=500,
                total_tokens=1000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        # Usage 1000 more (total 8000) -> remaining 2000 (20%) -> CONSTRAINED
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=500,
                completion_tokens=500,
                total_tokens=1000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CONSTRAINED)

        # Usage 1000 more (total 9000) -> remaining 1000 (10%) -> CRITICAL
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=500,
                completion_tokens=500,
                total_tokens=1000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

        # Usage 500 more (total 9500) -> remaining 500 (5%) -> CRITICAL
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=250,
                completion_tokens=250,
                total_tokens=500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

        # Usage 500 more (total 10000) -> remaining 0 (0%) -> EXHAUSTED
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=250,
                completion_tokens=250,
                total_tokens=500,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.EXHAUSTED)

    def test_multiple_configured_quotas_most_restrictive_tier_wins(self):
        manager = TokenBudgetManager(
            max_request_tokens=100000,
            safety_reserve_tokens=0,
            tpm_limit=10000,
            tpd_limit=100000,
        )

        start_time = 1000.0
        with patch.object(manager, "_now_ts", return_value=start_time):
            manager.record_actual_usage(
                LLMUsage(
                    prompt_tokens=45000,
                    completion_tokens=45000,
                    total_tokens=90000,
                    model="test",
                )
            )

        with patch.object(manager, "_now_ts", return_value=start_time + 61.0):
            self.assertEqual(manager.get_degradation_tier(), DegradationTier.CRITICAL)

    def test_disabled_quota_ignored(self):
        manager = TokenBudgetManager(
            tpm_limit=None,
            tpd_limit=10000,
        )
        manager.record_actual_usage(
            LLMUsage(
                prompt_tokens=2000,
                completion_tokens=2000,
                total_tokens=4000,
                model="test",
            )
        )
        self.assertEqual(manager.get_degradation_tier(), DegradationTier.NORMAL)

    def test_usage_snapshot_includes_degradation_tier(self):
        manager = TokenBudgetManager(tpm_limit=10000)
        snapshot = manager.get_usage_snapshot()
        self.assertEqual(snapshot["degradation_tier"], DegradationTier.NORMAL)


