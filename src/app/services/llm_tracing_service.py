import functools
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict

from src.app.services.langfuse_service import langfuse_service
from src.app.utils.logging_utils import loggers
from src.app.utils.tracing_context_utils import (
    request_context,
    user_query_context,
)


class LLMTracer:
    def __init__(self):
        self.traces = {}  # Storing the traces by their ids

    def get_trace(self, trace_id):
        return self.traces.get(trace_id)

    def add_trace(self, trace_id, trace_data):
        if trace_id not in self.traces:
            self.traces[trace_id] = {"id": trace_id, "llm_calls": []}
        self.traces[trace_id]["llm_calls"].append(trace_data)
        return self.traces[trace_id]


# Global tracer instance
tracer = LLMTracer()


def calculate_openai_price(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cache_input_tokens: int = 0,
) -> Dict[str, float]:

    pricing = {
        "gpt-3.5-turbo": {"input": 0.15, "cached_input": 0, "output": 0.6},
        "gpt-4o": {"input": 2.5, "cached_input": 1.25, "output": 10.0},
        "gpt-4o-mini": {"input": 0.15, "cached_input": 0.075, "output": 0.6},
        "gpt-4-turbo": {"input": 0.01, "cached_input": 0, "output": 0.03},
        "o1-2024-12-17": {"input": 15, "cached_input": 7.50, "output": 60},
        "o3-mini-2025-01-31": {
            "input": 1.1,
            "cached_input": 0.55,
            "output": 4.40,
        },
        "o1-mini-2024-09-12x": {
            "input": 1.1,
            "cached_input": 0.0,
            "output": 4.40,
        },
        "gpt-4.1": {"input": 2, "cached_input": 0.50, "output": 8},
        # when new openai models come then just add them over here
    }

    model_pricing = pricing.get(
        model_name, {"input": 0.0, "cached_input": 0.0, "output": 0.0}
    )  # Default fallback

    input_price = (input_tokens / 1000000) * model_pricing["input"]
    output_price = (output_tokens / 1000000) * model_pricing["output"]
    cached_input_price = (cache_input_tokens / 1000000) * model_pricing[
        "cached_input"
    ]
    total_price = input_price + output_price + cached_input_price

    return {
        "input": input_price,
        "output": output_price,
        "cached_input_price": cached_input_price,
        "total": total_price,
    }


def calculate_anthropic_price(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_input_tokens: int = 0,
    cache_read_input_tokens: int = 0,
) -> Dict[str, float]:
    """
    Calculate the price for Anthropic API usage including prompt caching.

    Args:
        model_name: The model used
        input_tokens: Regular input tokens (not cached)
        output_tokens: Output tokens
        cache_creation_input_tokens: Number of tokens used for cache creation (write)
        cache_read_input_tokens: Number of tokens accessed from cache (read)

    Returns:
        Dictionary with cost breakdown
    """
    # Base pricing for regular input/output
    base_pricing = {
        "claude-3-7-sonnet-20250219": {"input": 3, "output": 15},
        "claude-3-5-sonnet-20241022": {"input": 3, "output": 15},
        "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4},
        "claude-3-opus-20240229": {"input": 15, "output": 75},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    }

    # Cache pricing for different models
    cache_pricing = {
        "claude-3-7-sonnet-20250219": {"write": 3.75, "read": 0.3},
        "claude-3-5-haiku-20241022": {"write": 1, "read": 0.08},
        "claude-3-opus-20240229": {"write": 18.75, "read": 1.5},
        "claude-3-5-sonnet-20241022": {"write": 3.75, "read": 0.3},
        "claude-3-haiku-20240307": {"write": 1, "read": 0.08},
    }

    model_pricing = base_pricing.get(model_name, {"input": 0.0, "output": 0.0})
    cache_model_pricing = cache_pricing.get(
        model_name, {"write": 0.0, "read": 0.0}
    )

    # Calculate regular processing costs
    input_price = (input_tokens / 1000000) * model_pricing["input"]
    output_price = (output_tokens / 1000000) * model_pricing["output"]

    # Calculate cache-related costs
    cache_write_price = (
        cache_creation_input_tokens / 1000000
    ) * cache_model_pricing["write"]
    cache_read_price = (
        cache_read_input_tokens / 1000000
    ) * cache_model_pricing["read"]

    # Total cost
    total_price = (
        input_price + output_price + cache_write_price + cache_read_price
    )

    return {
        "input": input_price,
        "output": output_price,
        "cache_write": cache_write_price,
        "cache_read": cache_read_price,
        "total": total_price,
    }


def calculate_groq_price(
    model_name: str, input_tokens: int, output_tokens: int
) -> Dict[str, float]:

    pricing = {
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
        "gemma2-9b-it": {"input": 0.2, "output": 0.2},
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
        "llama3-70b-8192": {"input": 0.59, "output": 0.79},
        "llama-guard-3-8b": {"input": 0.2, "output": 0.2},
        "llama3-8b-8192": {"input": 0.05, "output": 0.08},
        "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
        "meta-llama/llama-4-maverick-17b-128e-instruct": {
            "input": 0.20,
            "output": 0.60,
        },
    }

    model_pricing = pricing.get(
        model_name, {"input": 0.0, "output": 0.0}
    )  # Default fallback

    input_price = (input_tokens / 1000000) * model_pricing["input"]
    output_price = (output_tokens / 1000000) * model_pricing["output"]
    total_price = input_price + output_price

    return {
        "input": round(input_price, 6),
        "output": round(output_price, 6),
        "total": round(total_price, 6),
    }


# Token parsers for different providers
def parse_openai_tokens(response_data: Dict[str, Any]) -> Dict[str, int]:
    usage = response_data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    cache_input_tokens = usage.get("prompt_tokens_details", {}).get(
        "cached_tokens", 0
    )

    return {
        "input": input_tokens,
        "output": output_tokens,
        "cache_input_tokens": cache_input_tokens,
        "total": usage.get("total_tokens", 0),
    }


def parse_groq_tokens(response_data: Dict[str, Any]) -> Dict[str, int]:
    usage = response_data.get("usage", {})
    return {
        "input": usage.get("prompt_tokens", 0),
        "output": usage.get("completion_tokens", 0),
        "total": usage.get("total_tokens", 0),
    }


def parse_anthropic_tokens(response_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Parse token usage information from Anthropic API response.
    Now includes cache-related token counts.
    """
    usage = response_data.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation_input_tokens = usage.get("cache_creation_input_tokens", 0)
    cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)

    return {
        "input": input_tokens,
        "output": output_tokens,
        "cache_creation_input_tokens": cache_creation_input_tokens,
        "cache_read_input_tokens": cache_read_input_tokens,
        "total": input_tokens + output_tokens,
    }


PROVIDER_CONFIGS = {
    "openai": {
        "token_parser": parse_openai_tokens,
        "price_calculator": calculate_openai_price,
        "response_extractor": lambda data: (
            data["choices"][0]["message"]["content"]
            if "choices" in data and data["choices"]
            else ""
        ),
    },
    "groq": {
        "token_parser": parse_groq_tokens,
        "price_calculator": calculate_groq_price,
        "response_extractor": lambda data: (
            data["choices"][0]["message"]["content"]
            if "choices" in data and data["choices"]
            else ""
        ),
    },
    "anthropic": {
        "token_parser": parse_anthropic_tokens,
        "price_calculator": calculate_anthropic_price,
        "response_extractor": lambda data: (
            data["content"][0]["text"]
            if "content" in data and data["content"]
            else ""
        ),
    },
    # Add other providers here
}


def register_provider(
    provider_name: str,
    token_parser: Callable,
    price_calculator: Callable,
    response_extractor: Callable,
):
    # Register a new LLM provider with configurations here
    PROVIDER_CONFIGS[provider_name] = {
        "token_parser": token_parser,
        "price_calculator": price_calculator,
        "response_extractor": response_extractor,
    }


def llm_streaming_tracing(provider: str):
    """
    Decorator for tracing streaming LLM API calls with provider-specific handling

    Args:
        provider: Name of the LLM provider (e.g., "anthropic", "openai")
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(
            self, user_prompt, system_prompt, thinking_budget=0, **params
        ):
            # Get trace ID from context
            user_query = user_query_context.get()
            id = request_context.get()
            trace_id = id

            # Get provider config
            provider_config = PROVIDER_CONFIGS.get(provider, {})
            if not provider_config:
                loggers["lfuse"].warning(
                    f"No config found for provider: {provider}, falling back to default handling"
                )
                # For generators, we need to yield from the original function instead of returning
                async for chunk in func(
                    self, user_prompt, system_prompt, thinking_budget, **params
                ):
                    yield chunk
                return  # This is OK - returning None from an async generator

            start_time = time.perf_counter()

            # Prepare initial generation data for starting the trace
            generation_data = {
                "model_name": getattr(self, f"{provider}_model", ""),
                "service_provider": provider,
                "input": user_query,
                "output": "",  # Initially empty, will be filled during streaming
                "system_prompt": system_prompt,
            }

            try:
                # Create the initial generation object to track streaming
                generation_info = (
                    await langfuse_service.create_streaming_generation(
                        trace_id,
                        generation_data,
                        f"{provider.capitalize()} Streaming Generation",
                    )
                )

                if not generation_info:
                    loggers["lfuse"].error(
                        "Failed to create streaming generation"
                    )
                    # Continue with the function call without tracing if generation creation fails
                    async for chunk in func(
                        self,
                        user_prompt,
                        system_prompt,
                        thinking_budget,
                        **params,
                    ):
                        yield chunk
                    return

                generation_object = generation_info["generation_object"]
                full_response = ""
                full_thinking = ""

                # Call the original streaming function and process chunks
                async for chunk_type, chunk_content in func(
                    self, user_prompt, system_prompt, thinking_budget, **params
                ):
                    # Update the accumulated response based on chunk type
                    if chunk_type == "text_delta":
                        full_response += chunk_content
                        await langfuse_service.update_streaming_generation(
                            generation_object, chunk=chunk_content
                        )
                    elif chunk_type == "thinking_delta":
                        full_thinking += chunk_content
                        await langfuse_service.update_streaming_generation(
                            generation_object, thinking=chunk_content
                        )

                    # Yield the chunk to the caller
                    yield chunk_type, chunk_content

                # Get end time for response time calculation
                end_time = time.perf_counter()
                response_time = end_time - start_time

                # After streaming is complete, get token usage and calculate price
                # This would typically come from a separate API call to get usage stats
                token_usage = await self._get_token_usage_for_response(
                    user_prompt, system_prompt, full_response, provider
                )

                if provider == "anthropic":
                    price_data = calculate_anthropic_price(
                        getattr(self, "anthropic_model", ""),
                        token_usage.get("input", 0),
                        token_usage.get("output", 0),
                        token_usage.get("cache_creation_input_tokens", 0),
                        token_usage.get("cache_read_input_tokens", 0),
                    )
                elif provider == "openai":
                    price_data = calculate_openai_price(
                        getattr(self, "openai_model", ""),
                        token_usage.get("input", 0),
                        token_usage.get("output", 0),
                        token_usage.get("cache_input_tokens", 0),
                    )
                else:
                    price_data = calculate_groq_price(
                        getattr(self, f"{provider}_model", ""),
                        token_usage.get("input", 0),
                        token_usage.get("output", 0),
                    )

                # Complete the generation with final stats
                await langfuse_service.update_streaming_generation(
                    generation_object,
                    final=True,
                    tokens=token_usage,
                    price=price_data,
                )

                # Record trace data for internal tracking
                trace_data = {
                    "id": trace_id,
                    "service_provider": provider,
                    "model_name": getattr(self, f"{provider}_model", ""),
                    "tokens": token_usage,
                    "price": price_data,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "user_query": user_query,
                    "llm_response": full_response,
                    "thinking": full_thinking if full_thinking else None,
                    "response_time": response_time,
                    "timestamp": datetime.now(
                        timezone(timedelta(hours=5, minutes=30))
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "is_streaming": True,
                }

                # Add to the tracer
                if trace_id:
                    tracer.add_trace(trace_id, trace_data)

                loggers["lfuse"].info(
                    f"Streaming trace completed for trace: {trace_id}"
                )

            except Exception as e:
                # Log the error
                error_trace = {
                    "id": trace_id,
                    "service_provider": provider,
                    "model_name": getattr(self, f"{provider}_model", ""),
                    "error": str(e),
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "user_query": user_query,
                    "timestamp": time.time(),
                    "is_streaming": True,
                }

                tracer.add_trace(trace_id, error_trace)
                loggers["lfuse"].error(f"Error in streaming trace: {e}")
                raise e

        return wrapper

    return decorator


def llm_tracing(provider: str):
    """
    Decorator for tracing LLM API calls with provider-specific handling

    Args:
        provider: Name of the LLM provider (e.g., "openai", "groq")
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(
            self, system_prompt, user_prompt, model_name, **params
        ):
            # Generate trace ID if not provided
            user_query = user_query_context.get()
            id = request_context.get()
            trace_id = id  # str(uuid.uuid4())

            if not trace_id or trace_id == "None" or trace_id == "":
                loggers["lfuse"].info(f"Skipping tracing - invalid trace ID: {trace_id}")
                return await func(self, system_prompt, user_prompt, model_name, **params)
            

            # Get provider config
            provider_config = PROVIDER_CONFIGS.get(provider, {})
            if not provider_config:
                loggers["lfuse"].warning(
                    f"No config found for provider: {provider}, falling back to default handling"
                )
                return await func(
                    self, system_prompt, user_prompt, model_name, **params
                )

            start_time = time.perf_counter()

            try:
                result = await func(
                    self, system_prompt, user_prompt, model_name, **params
                )

                end_time = time.perf_counter()
                response_time = end_time - start_time

                if isinstance(result, tuple):
                    response_data = result[0] if len(result) > 0 else None
                    raw_response = result[1] if len(result) > 1 else None
                    llm_response = response_data
                    tokens_data = (
                        provider_config["token_parser"](raw_response)
                        if raw_response
                        else {}
                    )
                else:
                    # case when function returns entire json response from llm
                    raw_response = result
                    llm_response = provider_config["response_extractor"](
                        raw_response
                    )
                    tokens_data = provider_config["token_parser"](raw_response)

                # Calculate price based on provider
                if provider == "anthropic":
                    price_data = provider_config["price_calculator"](
                        model_name,
                        tokens_data.get("input", 0),
                        tokens_data.get("output", 0),
                        tokens_data.get("cache_creation_input_tokens", 0),
                        tokens_data.get("cache_read_input_tokens", 0),
                    )
                elif provider == "openai":
                    price_data = provider_config["price_calculator"](
                        model_name,
                        tokens_data.get("input", 0),
                        tokens_data.get("output", 0),
                        tokens_data.get("cache_input_tokens", 0),
                    )
                else:
                    price_data = provider_config["price_calculator"](
                        model_name,
                        tokens_data.get("input", 0),
                        tokens_data.get("output", 0),
                    )

                ist = timezone(timedelta(hours=5, minutes=30))

                # Prepare generation data based on provider
                generation_data = {
                    "model_name": model_name,
                    "service_provider": provider,
                    "input": user_query,
                    "output": llm_response,
                    "system_prompt": system_prompt,
                    "price": price_data,
                    "tokens": tokens_data,
                    "start_time": datetime.fromtimestamp(start_time),
                    "end_time": datetime.fromtimestamp(end_time),
                }

                trace_data = {
                    "id": trace_id,
                    "service_provider": provider,
                    "model_name": model_name,
                    "tokens": tokens_data,
                    "price": price_data,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "user_query": user_query,
                    "llm_response": llm_response,
                    "response_time": response_time,
                    "timestamp": datetime.now(ist).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }

                # adding to the tracer
                if trace_id:
                    tracer.add_trace(trace_id, trace_data)

                ### ADD YOUR CUSTOM LOGIC FOR OBSERVABILITY BELOW ###
                try:
                    loggers["lfuse"].info(
                        f"Creating generation for trace: {trace_id}"
                    )

                    # Log detailed information including cache stats
                    if provider == "anthropic":
                        cache_stats = {
                            "Cache Creation Tokens": tokens_data.get(
                                "cache_creation_input_tokens", 0
                            ),
                            "Cache Read Tokens": tokens_data.get(
                                "cache_read_input_tokens", 0
                            ),
                            "Cache Write Cost": price_data.get(
                                "cache_write", 0
                            ),
                            "Cache Read Cost": price_data.get("cache_read", 0),
                        }
                        loggers["lfuse"].info(
                            f"Cache Statistics: {json.dumps(cache_stats, indent=2)}"
                        )
                    elif (
                        provider == "openai"
                        and tokens_data.get("cache_input_tokens", 0) > 0
                    ):
                        cache_stats = {
                            "Cache Input Tokens": tokens_data.get(
                                "cache_input_tokens", 0
                            ),
                            "Cache Input Cost": price_data.get(
                                "cached_input_price", 0
                            ),
                        }
                        loggers["lfuse"].info(
                            f"Cache Statistics: {json.dumps(cache_stats, indent=2)}"
                        )

                    loggers["lfuse"].info(f"Generation data: {generation_data}")

                    generation_id = (
                        await langfuse_service.create_generation_for_LLM(
                            trace_id,
                            generation_data,
                            f"{provider.capitalize()} Generation",
                        )
                    )
                    loggers["lfuse"].info(
                        f"Generation created with ID: {generation_id}"
                    )

                except Exception as e:
                    loggers["lfuse"].error(
                        f"Error while creating generation for trace: {trace_id}"
                    )

                ### ADD YOUR CUSTOM LOGIC FOR OBSERVABILITY ABOVE ###

                return result

            except Exception as e:
                # Log the error in the trace
                error_trace = {
                    "id": trace_id,
                    "service_provider": provider,
                    "model_name": model_name,
                    "error": str(e),
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "user_query": user_query,
                    "timestamp": time.time(),
                }
                tracer.add_trace(trace_id, error_trace)
                raise e

        return wrapper

    return decorator


# Helper function to easily get a trace by its id
def get_trace(trace_id: str) -> Dict[str, Any]:
    return tracer.get_trace(trace_id)
