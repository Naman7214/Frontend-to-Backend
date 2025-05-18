import time
from datetime import datetime

from fastapi import Depends, HTTPException
import json
from src.app.config.settings import settings
from src.app.models.domain.error import Error
from src.app.repositories.error_repository import ErrorRepo
from src.app.repositories.llm_usage_repository import LLMUsageRepository
from src.app.services.api_service import ApiService
from src.app.services.llm_tracing_service import llm_tracing


class AnthropicService:
    def __init__(
        self,
        api_service: ApiService = Depends(ApiService),
        llm_usage_repository: LLMUsageRepository = Depends(LLMUsageRepository),
        error_repo: ErrorRepo = Depends(ErrorRepo),
    ) -> None:
        self.api_service = api_service
        self.base_url = settings.ANTHROPIC_BASE_URL
        self.messages_endpoint = settings.ANTHROPIC_MESSAGES_ENDPOINT
        self.anthropic_model = settings.ANTHROPIC_MODEL
        self.llm_usage_repository = llm_usage_repository
        self.error_repo = error_repo

    @llm_tracing(provider="anthropic")
    async def _completions(
        self,
        system_prompt: str,
        user_prompt: str,
        model_name: str,
        stream=False,
        thinking_budget=0,
        **params,
    ):
        """
        This method is responsible for sending a POST request to the Anthropic API
        to get completions for the given prompt.
        :param prompt: The prompt to get completions for.
        :param params: The optional parameters.
        :return: The completions for the given prompt.
        """
        url = f"{self.base_url}{self.messages_endpoint}"

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": model_name,
            "max_tokens": 17000,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        }
                    ],
                }
            ],
            **{k: v for k, v in params.items()},
            # **params
        }

        if thinking_budget > 1024:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }

        try:

            start_time = time.perf_counter()
            response = await self.api_service.post(
                url=url, headers=headers, data=payload
            )
            end_time = time.perf_counter()
            duration = end_time - start_time

            usage = response.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_creation_input_tokens = usage.get(
                "cache_creation_input_tokens", 0
            )
            cache_read_input_tokens = usage.get("cache_read_input_tokens", 0)

            total_tokens = (
                input_tokens
                + output_tokens
                + cache_creation_input_tokens
                + cache_read_input_tokens
            )
            llm_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cache_creation_input_tokens": cache_creation_input_tokens,
                "cache_read_input_tokens": cache_read_input_tokens,
                "duration": duration,
                "provider": "Anthropic",
                "model": self.anthropic_model,
                "created_at": datetime.utcnow(),
            }
            await self.llm_usage_repository.add_llm_usage(llm_usage)
            return response
        except Exception as e:
            await self.error_repo.insert_error(
                error=Error(
                    f"Error while sending a POST request to the Anthropic API: {str(e)}"
                )
            )

            raise HTTPException(
                status_code=500,
                detail=f"Error while sending a POST request to the Anthropic API: {str(e)}",
            )

    async def completions(
        self,
        system_prompt: str,
        user_prompt: str,
        stream=False,
        thinking_budget=0,
        **params,
    ):
        response = await self._completions(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_name=settings.ANTHROPIC_MODEL,
            stream=stream,
            thinking_budget=thinking_budget,
            **params,
        )
        return response["content"][0]["text"]

    async def stream_completions(
        self, user_prompt: str, system_prompt: str, thinking_budget=0, **params
    ):
        url = f"{self.base_url}{self.messages_endpoint}"

        headers = {
            "x-api-key": settings.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.anthropic_model,
            "max_tokens": 63000,
            "stream": True,
            "system": [
                {
                    "type": "text",
                    "text": system_prompt,
                }
            ],
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt,
                        }
                    ],
                }
            ],
            **{k: v for k, v in params.items()},
        }

        if thinking_budget > 1024:
            payload["thinking"] = {
                "type": "enabled",
                "budget_tokens": thinking_budget,
            }

        try:
            start_time = time.perf_counter()
            input_tokens = 0
            output_tokens = 0
            cache_creation_input_tokens = 0
            cache_read_input_tokens = 0

            async for line in self.api_service.post_stream(
                url=url, headers=headers, data=payload
            ):
                if not line.strip():
                    continue

                if line.startswith("data"):
                    try:
                        json_data = line[5:].strip()
                        if json_data:
                            data = json.loads(json_data)

                            # Extract token usage from message_start event
                            if data.get("type") == "message_start":
                                message = data.get("message", {})
                                usage = message.get("usage", {})
                                input_tokens = usage.get("input_tokens", 0)
                                cache_creation_input_tokens = usage.get(
                                    "cache_creation_input_tokens", 0
                                )
                                cache_read_input_tokens = usage.get(
                                    "cache_read_input_tokens", 0
                                )
                                # We get initial output_tokens, but will update from message_delta

                            # Extract final output token count from message_delta event
                            if data.get("type") == "message_delta":
                                usage = data.get("usage", {})
                                if "output_tokens" in usage:
                                    output_tokens = usage.get(
                                        "output_tokens", 0
                                    )
                                # Update cache tokens if provided in delta
                                if "cache_creation_input_tokens" in usage:
                                    cache_creation_input_tokens = usage.get(
                                        "cache_creation_input_tokens", 0
                                    )
                                if "cache_read_input_tokens" in usage:
                                    cache_read_input_tokens = usage.get(
                                        "cache_read_input_tokens", 0
                                    )

                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield ("text_delta", delta.get("text", ""))

                            if (
                                data.get("type") == "content_block_delta"
                                and data.get("delta", {}).get("type")
                                == "thinking_delta"
                            ):
                                yield (
                                    "thinking_delta",
                                    data.get("delta", {}).get("thinking", ""),
                                )

                            # Save usage data when streaming is complete
                            if data.get("type") == "message_stop":
                                end_time = time.perf_counter()
                                duration = end_time - start_time
                                total_tokens = (
                                    input_tokens
                                    + output_tokens
                                    + cache_creation_input_tokens
                                    + cache_read_input_tokens
                                )

                                llm_usage = {
                                    "input_tokens": input_tokens,
                                    "output_tokens": output_tokens,
                                    "total_tokens": total_tokens,
                                    "cache_creation_input_tokens": cache_creation_input_tokens,
                                    "cache_read_input_tokens": cache_read_input_tokens,
                                    "duration": duration,
                                    "provider": "Anthropic",
                                    "model": self.anthropic_model,
                                    "created_at": datetime.utcnow(),
                                }
                                await self.llm_usage_repository.add_llm_usage(
                                    llm_usage
                                )
                                yield ("usage_info", llm_usage)

                    except json.JSONDecodeError:
                        await self.error_repo.insert_error(
                            error=Error(
                                f"Error while decoding json response the Anthropic Streaming API"
                            )
                        )
                    except Exception as e:
                        await self.error_repo.insert_error(
                            error=Error(
                                f"Error while sending a POST request to the Anthropic Streaming API: {str(e)}"
                            )
                        )
                        continue

        except Exception as e:
            await self.error_repo.insert_error(
                error=Error(
                    f"Error while streaming from Anthropic API: {str(e)}"
                )
            )
            raise HTTPException(
                status_code=500,
                detail=f"Error while streaming from Anthropic API: {str(e)}",
            )
