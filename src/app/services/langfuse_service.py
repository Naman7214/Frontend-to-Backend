from typing import Any, Dict, Optional

from fastapi import Depends

from langfuse import Langfuse
from src.app.config.settings import settings
from src.app.repositories.error_repository import ErrorRepo
from src.app.utils.logging_utils import loggers
from src.app.utils.tracing_context_utils import tracer_context


class LangfuseService:
    def __init__(self, error_repo: ErrorRepo = Depends(ErrorRepo)) -> None:
        self.langfuse_client = self._initialize_langfuse_client()
        self.error_repo = error_repo

    def _initialize_langfuse_client(self):
        return Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            release=settings.APP_VERSION,
        )

    # Add a trace validation helper method
    def is_valid_trace_id(self, trace_id: str) -> bool:
        """Validates if a trace ID should be used for creating traces"""
        return trace_id is not None and trace_id != "None" and trace_id != ""

    async def create_generation_for_LLM(
        self, trace_id: str, generation_data: Dict[str, Any], name: str
    ) -> Optional[str]:
        # Skip if invalid trace ID
        if not self.is_valid_trace_id(trace_id):
            loggers["lfuse"].info(
                f"Skipping trace creation - invalid trace ID: {trace_id}"
            )
            return None

        loggers["lfuse"].info(
            f"entering create_generation with trace_id: {trace_id}"
        )

        loggers["lfuse"].info(f"langfuse_client: {self.langfuse_client}")

        try:
            # time.sleep(10)
            trace = tracer_context.get()
            loggers["lfuse"].info(
                f"trace object retrieved inside LLM calling: {trace}"
            )
            trace.update(
                output=generation_data["output"],
            )
        except Exception as e:
            loggers["lfuse"].error(f"error fetching trace: {e}")
            return None

        loggers["lfuse"].info(f"trace object retrieved: {trace}")

        generation_object = self.langfuse_client.generation(
            trace_id=trace_id,
            name=name,
        )

        # Prepare usage_details and cost_details based on the provider
        provider = generation_data.get("service_provider", "")

        usage_details = {
            "input_token": generation_data["tokens"]["input"],
            "output_token": generation_data["tokens"]["output"],
            "total_token": generation_data["tokens"]["total"],
        }

        cost_details = {
            "input_cost": generation_data["price"]["input"],
            "output_cost": generation_data["price"]["output"],
            "total_cost": generation_data["price"]["total"],
        }

        metadata = {
            "provider": provider,
            "cost": generation_data["price"]["total"],
            "input_token": generation_data["tokens"]["input"],
            "output_token": generation_data["tokens"]["output"],
            "total_token": generation_data["tokens"]["total"],
        }

        # Add provider-specific cache information
        if provider == "anthropic":
            usage_details.update(
                {
                    "cache_creation_input_tokens": generation_data[
                        "tokens"
                    ].get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": generation_data["tokens"].get(
                        "cache_read_input_tokens", 0
                    ),
                }
            )

            cost_details.update(
                {
                    "cache_write_cost": generation_data["price"].get(
                        "cache_write", 0
                    ),
                    "cache_read_cost": generation_data["price"].get(
                        "cache_read", 0
                    ),
                }
            )

            metadata.update(
                {
                    "cache_creation_input_tokens": generation_data[
                        "tokens"
                    ].get("cache_creation_input_tokens", 0),
                    "cache_read_input_tokens": generation_data["tokens"].get(
                        "cache_read_input_tokens", 0
                    ),
                    "cache_write_cost": generation_data["price"].get(
                        "cache_write", 0
                    ),
                    "cache_read_cost": generation_data["price"].get(
                        "cache_read", 0
                    ),
                }
            )
        elif provider == "openai":
            usage_details.update(
                {
                    "cache_input_tokens": generation_data["tokens"].get(
                        "cache_input_tokens", 0
                    ),
                }
            )

            cost_details.update(
                {
                    "cached_input_price": generation_data["price"].get(
                        "cached_input_price", 0
                    ),
                }
            )

            metadata.update(
                {
                    "cache_input_tokens": generation_data["tokens"].get(
                        "cache_input_tokens", 0
                    ),
                    "cached_input_price": generation_data["price"].get(
                        "cached_input_price", 0
                    ),
                }
            )

        generation_object.end(
            model=generation_data["model_name"],
            input=generation_data["input"],
            output=generation_data["output"],
            usage_details=usage_details,
            cost_details=cost_details,
            metadata=metadata,
        )

        # time.sleep(10)
        loggers["lfuse"].info(f"generation object created: {generation_object}")
        return generation_object.id

    async def create_streaming_generation(
        self, trace_id: str, generation_data: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Create a streaming generation and return the generation object for updates"""
        loggers["lfuse"].info(
            f"Creating streaming generation with trace_id: {trace_id}"
        )

        try:
            trace = tracer_context.get()
            loggers["lfuse"].info(
                f"trace object retrieved for streaming: {trace}"
            )
        except Exception as e:
            loggers["lfuse"].error(f"error fetching trace for streaming: {e}")
            return None

        generation_object = self.langfuse_client.generation(
            trace_id=trace_id,
            name=name,
        )

        # Start the generation with input data
        generation_object.update(
            model=generation_data["model_name"],
            input=generation_data["input"],
            metadata={
                "provider": generation_data.get("service_provider", ""),
                "is_streaming": True,
                "system_prompt": generation_data.get("system_prompt", ""),
            },
        )

        loggers["lfuse"].info(
            f"Streaming generation object created: {generation_object.id}"
        )

        return {
            "generation_id": generation_object.id,
            "generation_object": generation_object,
        }

    async def update_streaming_generation(
        self,
        generation_object,
        chunk: str = None,
        thinking: str = None,
        final: bool = False,
        tokens: Dict[str, int] = None,
        price: Dict[str, float] = None,
    ):
        """Update a streaming generation with new chunks of data"""
        try:
            if chunk:
                # Update with the new chunk
                current_output = generation_object.get("output", "")
                updated_output = current_output + chunk
                generation_object.update(output=updated_output)

            if thinking:
                # Update thinking output if provided
                current_thinking = generation_object.get("metadata", {}).get(
                    "thinking", ""
                )
                updated_thinking = current_thinking + thinking
                metadata = generation_object.get("metadata", {})
                metadata["thinking"] = updated_thinking
                generation_object.update(metadata=metadata)

            if final:
                # Finalize the generation with token and price information
                provider = generation_object.get("metadata", {}).get(
                    "provider", ""
                )

                usage_details = {
                    "input_token": tokens["input"],
                    "output_token": tokens["output"],
                    "total_token": tokens["total"],
                }

                cost_details = {
                    "input_cost": price["input"],
                    "output_cost": price["output"],
                    "total_cost": price["total"],
                }

                metadata = generation_object.get("metadata", {})
                metadata.update(
                    {
                        "cost": price["total"],
                        "input_token": tokens["input"],
                        "output_token": tokens["output"],
                        "total_token": tokens["total"],
                        "streaming_completed": True,
                    }
                )

                # Add provider-specific cache information
                if provider == "anthropic":
                    usage_details.update(
                        {
                            "cache_creation_input_tokens": tokens.get(
                                "cache_creation_input_tokens", 0
                            ),
                            "cache_read_input_tokens": tokens.get(
                                "cache_read_input_tokens", 0
                            ),
                        }
                    )

                    cost_details.update(
                        {
                            "cache_write_cost": price.get("cache_write", 0),
                            "cache_read_cost": price.get("cache_read", 0),
                        }
                    )

                    metadata.update(
                        {
                            "cache_creation_input_tokens": tokens.get(
                                "cache_creation_input_tokens", 0
                            ),
                            "cache_read_input_tokens": tokens.get(
                                "cache_read_input_tokens", 0
                            ),
                            "cache_write_cost": price.get("cache_write", 0),
                            "cache_read_cost": price.get("cache_read", 0),
                        }
                    )
                elif provider == "openai":
                    usage_details.update(
                        {
                            "cache_input_tokens": tokens.get(
                                "cache_input_tokens", 0
                            ),
                        }
                    )

                    cost_details.update(
                        {
                            "cached_input_price": price.get(
                                "cached_input_price", 0
                            ),
                        }
                    )

                    metadata.update(
                        {
                            "cache_input_tokens": tokens.get(
                                "cache_input_tokens", 0
                            ),
                            "cached_input_price": price.get(
                                "cached_input_price", 0
                            ),
                        }
                    )

                generation_object.end(
                    usage_details=usage_details,
                    cost_details=cost_details,
                    metadata=metadata,
                )

                loggers["lfuse"].info(
                    f"Streaming generation finalized: {generation_object.id}"
                )

        except Exception as e:
            loggers["lfuse"].error(f"Error updating streaming generation: {e}")

    async def create_span_for_vectorDB(
        self, trace_id: str, span_data: Dict[str, Any], name: str
    ) -> Optional[str]:
        loggers["lfuse"].info(
            f"entering create_span_for_vectorDB with trace_id: {trace_id}"
        )

        span_object = self.langfuse_client.span(
            trace_id=trace_id,
            name=name,
        )

        span_object.end(
            input=span_data["query"],
            output=span_data["response"][0]["text"],
            start_time=span_data["start_time"],
            end_time=span_data["end_time"],
            metadata={
                "operation_type": span_data["operation_type"],
                "provider": span_data["service_provider"],
                "cost": span_data["price"],
                "read_units": span_data["units"],
            },
        )

        # time.sleep(10)
        loggers["lfuse"].info(f"span object created: {span_object}")
        return span_object.id

    async def create_span_for_embedding(
        self, trace_id: str, span_data: Dict[str, Any], name: str
    ) -> Optional[str]:
        loggers["lfuse"].info(
            f"entering create_span_for_embedding with trace_id: {trace_id}"
        )

        loggers["lfuse"].info(f"langfuse_client: {self.langfuse_client}")

        try:
            # time.sleep(10)
            trace = tracer_context.get()
            loggers["lfuse"].info(
                f"trace object retrieved inside embedding: {trace}"
            )
            trace.update(
                input=span_data["input"],
            )
        except Exception as e:
            loggers["lfuse"].error(f"error fetching trace: {e}")
            return None

        loggers["lfuse"].info(f"trace object retrieved: {trace}")

        span_object = self.langfuse_client.span(
            trace_id=trace_id,
            name=name,
        )

        span_object.end(
            input=span_data["input"],
            start_time=span_data["start_time"],
            end_time=span_data["end_time"],
            metadata={
                "provider": span_data["service_provider"],
                "model_name": span_data["model_name"],
                "input count": span_data["input_count"],
                "cost": span_data["price"]["total"],
                "token usage": span_data["tokens"],
                "price": span_data["price"],
                "embedding_dimensions": span_data["embedding_dimensions"],
                "response_time": span_data["response_time"],
                "timestamp": span_data["timestamp"],
            },
        )

        # time.sleep(10)
        loggers["lfuse"].info(f"span object created: {span_object}")
        return span_object.id

    async def create_span_for_reranking(
        self, trace_id: str, span_data: Dict[str, Any], name: str
    ) -> Optional[str]:
        loggers["lfuse"].info(
            f"entering create_span_for_reranking with trace_id: {trace_id}"
        )

        span_object = self.langfuse_client.span(
            trace_id=trace_id,
            name=name,
        )

        span_object.end(
            input={
                "query": span_data["query"],
                "documents": span_data["documents"],
            },
            output=span_data["rerank_results"],
            start_time=span_data["start_time"],
            end_time=span_data["end_time"],
            metadata={
                "provider": span_data["service_provider"],
                "model_name": span_data["model_name"],
                "output_count": span_data["document_count"],
                "cost": span_data["price"],
                "token usage": span_data["tokens"]["rerank_units"],
                "response_time": span_data["response_time"],
                "timestamp": span_data["timestamp"],
                "top_n": span_data["top_n"],
            },
        )

        # time.sleep(10)
        loggers["lfuse"].info(f"span object created: {span_object}")
        return span_object.id


langfuse_service = LangfuseService()
