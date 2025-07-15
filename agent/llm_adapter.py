import os
from typing import Any, Dict, Optional, AsyncGenerator
from abc import ABC, abstractmethod
import asyncio

import openai
from anthropic import AsyncAnthropic
from langchain.llms.base import LLM
from langchain_openai import ChatOpenAI
from langchain.callbacks.manager import CallbackManagerForLLMRun

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def complete(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def complete_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation."""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def complete(self, prompt: str, **kwargs) -> str:
        # Handle response_format parameter - convert 'json' to 'json_object'
        response_format = kwargs.get("response_format", "text")
        if response_format == "json":
            response_format = "json_object"
        
        response = await self.client.chat.completions.create(
            model=kwargs.get("model", "gpt-4-turbo-preview"),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            response_format={"type": response_format}
        )
        return response.choices[0].message.content
    
    async def complete_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=kwargs.get("model", "gpt-4-turbo-preview"),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            stream=True
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

class ClaudeProvider(LLMProvider):
    """Claude provider implementation."""
    
    def __init__(self):
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    async def complete(self, prompt: str, **kwargs) -> str:
        response = await self.client.messages.create(
            model=kwargs.get("model", "claude-3-opus-20240229"),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        return response.content[0].text
    
    async def complete_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        stream = await self.client.messages.stream(
            model=kwargs.get("model", "claude-3-opus-20240229"),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        
        async with stream as s:
            async for chunk in s:
                if chunk.type == "content_block_delta":
                    yield chunk.delta.text

class LLMAdapter:
    """Unified interface for LLM providers with LangChain support."""
    
    def __init__(self, provider: str = "openai"):
        self.provider_name = provider
        self.provider = self._init_provider(provider)
        self.llm = self._init_langchain_llm(provider)
    
    def _init_provider(self, provider: str) -> LLMProvider:
        if provider == "openai":
            return OpenAIProvider()
        elif provider == "claude":
            return ClaudeProvider()
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _init_langchain_llm(self, provider: str) -> LLM:
        """Initialize LangChain LLM for structured output parsing."""
        if provider == "openai":
            return ChatOpenAI(
                model_name="gpt-4-turbo-preview",
                temperature=0.7,
                openai_api_key=os.getenv("OPENAI_API_KEY")
            )
        elif provider == "claude":
            # For Claude, we'll create a custom LangChain wrapper
            return CustomClaudeLLM()
        else:
            raise ValueError(f"Unknown provider for LangChain: {provider}")
    
    async def complete(self, prompt: str, **kwargs) -> str:
        """Complete a prompt and return the full response."""
        return await self.provider.complete(prompt, **kwargs)
    
    async def complete_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """Complete a prompt and stream the response."""
        async for chunk in self.provider.complete_stream(prompt, **kwargs):
            yield chunk
    
    def switch_provider(self, provider: str):
        """Switch to a different LLM provider."""
        self.provider_name = provider
        self.provider = self._init_provider(provider)
        self.llm = self._init_langchain_llm(provider)

class CustomClaudeLLM(LLM):
    """Custom LangChain wrapper for Claude."""
    
    client: Optional[AsyncAnthropic] = None
    
    @property
    def _llm_type(self) -> str:
        return "claude"
    
    def __init__(self):
        super().__init__()
        self.client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    def _call(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Synchronous call - convert async to sync."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._acall(prompt, stop, run_manager, **kwargs))
        finally:
            loop.close()
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str:
        """Async call to Claude."""
        response = await self.client.messages.create(
            model=kwargs.get("model", "claude-3-opus-20240229"),
            messages=[{"role": "user", "content": prompt}],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096)
        )
        return response.content[0].text