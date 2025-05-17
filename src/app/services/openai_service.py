import json
import time
from datetime import datetime

from fastapi import Depends, HTTPException

from src.app.config.settings import settings
from src.app.repositories.llm_usage_repository import LLMUsageRepository
from src.app.services.api_service import ApiService
from src.app.services.llm_tracing_service import llm_tracing


class OpenAIService:
    def __init__(
        self,
        api_service: ApiService = Depends(),
        llm_usage_repository: LLMUsageRepository = Depends(),
    ) -> None:
        self.api_service = api_service
        self.base_url = settings.OPENAI_BASE_URL
        self.completion_endpoint = settings.OPENAI_COMPLETION_ENDPOINT
        self.openai_model = settings.OPENAI_MODEL
        self.llm_usage_repository = llm_usage_repository

    @llm_tracing(provider="openai")
    async def _completions(
        self,
        user_prompt: str,
        system_prompt: str,
        model_name: str,
        **params,
    ) -> dict:
        """
        This method is responsible for sending a POST request to the OpenAI API
        to get completions for the given prompt.
        :param prompt: The prompt to get completions for.
        :param params: The optional parameters.
        :return: The completions for the given prompt.
        """
        url = f"{self.base_url}{self.completion_endpoint}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        }

        payload = {
            "model": self.openai_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": user_prompt},
            ],
            **params,
        }
        try:
            start_time = time.perf_counter()

            response = await self.api_service.post(
                url=url, headers=headers, data=payload
            )

            end_time = time.perf_counter()
            duration = end_time - start_time

            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            llm_usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "duration": duration,
                "provider": "OpenAI",
                "model": self.openai_model,
                "created_at": datetime.utcnow(),
            }
            await self.llm_usage_repository.add_llm_usage(llm_usage)

            return response
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error while sending a POST request to the OpenAI API: {str(e)} \n error from openai_service in completions()",
            )

    async def completions(
        self,
        user_prompt: str,
        system_prompt: str,
        **params,
    ):
        response = await self._completions(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            model_name=settings.OPENAI_MODEL,
            **params,
        )
        return response["choices"][0]["message"]["content"]