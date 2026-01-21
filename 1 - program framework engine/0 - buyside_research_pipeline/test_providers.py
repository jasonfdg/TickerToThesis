#!/usr/bin/env python3
"""
Test Provider Connections
=========================
Quick test to verify all providers are configured and working.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from providers import ProviderFactory

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


async def test_providers():
    """Test all provider connections."""
    factory = ProviderFactory()

    print("=" * 60)
    print("TESTING PROVIDER CONNECTIONS")
    print("=" * 60)

    # Check API keys
    print("\nAPI Key Status:")
    print(f"  ANTHROPIC_API_KEY: {'Set' if os.getenv('ANTHROPIC_API_KEY') else 'MISSING'}")
    print(f"  OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'MISSING'}")
    print(f"  GOOGLE_API_KEY: {'Set' if os.getenv('GOOGLE_API_KEY') else 'MISSING'}")
    print(f"  PERPLEXITY_API_KEY: {'Set' if os.getenv('PERPLEXITY_API_KEY') else 'MISSING'}")

    print("\nConnection Tests:")

    # Test each provider
    results = await factory.test_all_connections()

    for provider, success in results.items():
        status = "✓ OK" if success else "✗ FAILED"
        print(f"  {provider}: {status}")

    print("\n" + "=" * 60)

    # Quick generation test on working providers
    print("\nQuick Generation Test (working providers):")

    for provider, success in results.items():
        if success:
            try:
                response = await factory.generate(
                    provider_type=provider,
                    model=None,  # Use default
                    system_prompt="You are a helpful assistant.",
                    user_prompt="What is 2+2? Reply with just the number.",
                    max_tokens=10,
                )
                print(f"  {provider}: '{response.content.strip()}' ({response.token_usage.total_tokens} tokens)")
            except Exception as e:
                print(f"  {provider}: Generation failed - {e}")

    print("\n" + "=" * 60)
    print("Provider setup complete!")

    # Print provider mapping
    print("\nAnalyst Provider Mapping:")
    from providers import ANALYST_PROVIDERS
    for type_id, (provider, model) in ANALYST_PROVIDERS.items():
        print(f"  Type {type_id}: {provider}/{model}")

    print("\nRole Provider Mapping:")
    from providers import ROLE_PROVIDERS
    from models import AgentRole
    for role, (provider, model) in ROLE_PROVIDERS.items():
        print(f"  {role.value}: {provider}/{model}")

    factory.close_all()


if __name__ == "__main__":
    asyncio.run(test_providers())
