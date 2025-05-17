from src.app.services.openai_service import OpenAIService
from fastapi import Depends
from src.app.prompts.set_priority_prompts import (
    SET_PRIORITY_SYSTEM_PROMPT,
    SET_PRIORITY_USER_PROMPT,
)
from src.app.utils.response_parser import parse_response

class SetPriorityUseCase:
     
    def __init__(self, openai_service: OpenAIService = Depends(OpenAIService)):
        self.openai_service = openai_service
	
    async def set_priority(self, data: dict):
        user_prompts = SET_PRIORITY_USER_PROMPT.format(context=data)
        response = await self.openai_service._completions(
            user_prompt=user_prompts,
            system_prompt=SET_PRIORITY_SYSTEM_PROMPT,
        )
        parsed_response = parse_response(response)
        return parsed_response
		