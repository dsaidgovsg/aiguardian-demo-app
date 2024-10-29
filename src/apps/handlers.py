import os
from collections.abc import Callable
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
from uuid import UUID

import chainlit as cl
from chainlit.config import config
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.outputs import GenerationChunk
from langchain_core.outputs import LLMResult


class AnswerCallbackHandler(AsyncCallbackHandler):
    message: cl.Message
    elements: List[cl.element.Element] = []
    on_message_complete: Callable[[cl.Message], Any] = lambda message: None

    def __init__(self, on_message_complete: Callable[[cl.Message], Any]):
        super().__init__()
        self.on_message_complete = on_message_complete

    async def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        self.message = cl.Message(
            content="",
            author=(
                metadata["run_name"]
                if os.getenv("LOG_LEVEL") == "DEBUG"
                and metadata is not None
                and "run_name" in metadata
                else config.ui.name
            ),
            elements=self.elements or [],
        )

    async def on_llm_new_token(
        self,
        token: str,
        *,
        chunk: Optional[Union[GenerationChunk, ChatGenerationChunk]] = None,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        if not self.message.content:
            await cl.user_session.get("waiting_message").remove()

            await self.message.send()

        await self.message.stream_token(token)

    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> None:
        await self.message.update()
        await self.on_message_complete(self.message)
