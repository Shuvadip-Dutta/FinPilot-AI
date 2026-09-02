from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from apps.ai.services.sentiment import FinancialSentimentClassifier
from apps.ai.services.schemas import SentimentResult


class FinancialSentimentClassifierTestCase(SimpleTestCase):

    def test_classifier_can_be_instantiated_without_inference(self):
        classifier = FinancialSentimentClassifier(model_name="test-model")

        self.assertEqual(classifier.model_name, "test-model")
        self.assertIsNone(classifier._model)

    @patch("transformers.pipeline")
    def test_injected_backend_works(self, mock_pipeline):
        mock_model = MagicMock(return_value=[{"label": "LABEL_1", "score": 0.87}])
        mock_pipeline.return_value = mock_model

        classifier = FinancialSentimentClassifier(model_name="test-model")
        result = classifier.classify("The company reported strong earnings.")

        self.assertIsInstance(result, SentimentResult)
        self.assertEqual(result.label, "positive")
        self.assertEqual(result.confidence, 0.87)
        mock_pipeline.assert_called_once_with(
            "text-classification",
            model="test-model",
            device="cpu",
        )

    def test_empty_input_is_handled(self):
        classifier = FinancialSentimentClassifier(model_name="test-model")

        result = classifier.classify("   ")

        self.assertEqual(result.label, "neutral")
        self.assertEqual(result.confidence, 0.0)

    @override_settings(FINANCIAL_SENTIMENT_MODEL="custom/sentiment-model")
    def test_model_configuration_is_read_from_django_settings(self):
        classifier = FinancialSentimentClassifier()

        self.assertEqual(classifier.model_name, "custom/sentiment-model")

    @patch("transformers.pipeline")
    def test_model_loading_is_lazy(self, mock_pipeline):
        classifier = FinancialSentimentClassifier(model_name="test-model")
        self.assertIsNone(classifier._model)

        classifier.classify("Strong results.")

        self.assertIsNotNone(classifier._model)
        mock_pipeline.assert_called_once()
