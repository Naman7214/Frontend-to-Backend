from fastapi import Depends

from src.app.prompts.set_priority_prompts import (
    SET_PRIORITY_SYSTEM_PROMPT,
    SET_PRIORITY_USER_PROMPT,
)
from src.app.services.openai_service import OpenAIService
from src.app.utils.response_parser import parse_response
from src.app.utils.store_response import store_json_response


class SetPriorityUseCase:

    def __init__(self, openai_service: OpenAIService = Depends(OpenAIService)):
        self.openai_service = openai_service

    async def set_priority(self, data: dict):
        user_prompts = SET_PRIORITY_USER_PROMPT.format(context=data)
        response = await self.openai_service.completions(
            user_prompt=user_prompts,
            system_prompt=SET_PRIORITY_SYSTEM_PROMPT,
        )
        parsed_response = parse_response(response)
        params = {
            "response": parsed_response,
            "file_path": "intermediate_outputs/set_priority_end_points.json",
        }
        await store_json_response(params)
        return parsed_response
