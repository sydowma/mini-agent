"""Tests for provider detection and CLI utilities."""

import pytest
from mini_agent.cli import detect_provider, MODEL_PROVIDERS


class TestProviderDetection:
    def test_openai_models(self):
        """Test OpenAI model detection."""
        assert detect_provider("gpt-4o") == "openai"
        assert detect_provider("gpt-4o-mini") == "openai"
        assert detect_provider("gpt-4-turbo") == "openai"
        assert detect_provider("gpt-4") == "openai"
        assert detect_provider("gpt-3.5-turbo") == "openai"
        assert detect_provider("o1") == "openai"
        assert detect_provider("o1-mini") == "openai"
        assert detect_provider("o1-preview") == "openai"

    def test_anthropic_models(self):
        """Test Anthropic model detection."""
        assert detect_provider("claude-sonnet-4-20250514") == "anthropic"
        assert detect_provider("claude-sonnet-4") == "anthropic"
        assert detect_provider("claude-3-5-sonnet-20241022") == "anthropic"
        assert detect_provider("claude-3-5-sonnet") == "anthropic"
        assert detect_provider("claude-3-5-haiku-20241022") == "anthropic"
        assert detect_provider("claude-3-5-haiku") == "anthropic"
        assert detect_provider("claude-3-opus-20240229") == "anthropic"
        assert detect_provider("claude-3-opus") == "anthropic"
        assert detect_provider("claude-3-sonnet") == "anthropic"
        assert detect_provider("claude-3-haiku") == "anthropic"

    def test_zhipu_glm_models(self):
        """Test Zhipu AI GLM model detection (Anthropic-compatible)."""
        assert detect_provider("glm-4-plus") == "anthropic"
        assert detect_provider("glm-4-air") == "anthropic"
        assert detect_provider("glm-4-airx") == "anthropic"
        assert detect_provider("glm-4-flash") == "anthropic"
        assert detect_provider("glm-4-long") == "anthropic"
        assert detect_provider("glm-4v-plus") == "anthropic"
        assert detect_provider("glm-4v-flash") == "anthropic"
        assert detect_provider("glm-z1-air") == "anthropic"
        assert detect_provider("glm-z1-airx") == "anthropic"
        assert detect_provider("glm-z1-flash") == "anthropic"

    def test_prefix_detection(self):
        """Test detection by model name prefix."""
        # Unknown GPT models should default to openai
        assert detect_provider("gpt-5") == "openai"
        assert detect_provider("gpt-new-model") == "openai"

        # Unknown Claude models should default to anthropic
        assert detect_provider("claude-new-model") == "anthropic"
        assert detect_provider("claude-4-opus") == "anthropic"

        # Unknown GLM models should default to anthropic
        assert detect_provider("glm-new-model") == "anthropic"

    def test_case_insensitive(self):
        """Test case insensitive detection."""
        assert detect_provider("GPT-4O") == "openai"
        assert detect_provider("Claude-3-Opus") == "anthropic"
        assert detect_provider("O1-MINI") == "openai"
        assert detect_provider("GLM-4-PLUS") == "anthropic"

    def test_unknown_model_defaults_to_anthropic(self):
        """Test that unknown models default to Anthropic (supports custom endpoints)."""
        assert detect_provider("unknown-model") == "anthropic"
        assert detect_provider("llama-2") == "anthropic"
        assert detect_provider("mistral") == "anthropic"

    def test_model_provider_mapping_completeness(self):
        """Test that all models in the mapping are detected correctly."""
        for model, expected_provider in MODEL_PROVIDERS.items():
            assert detect_provider(model) == expected_provider
