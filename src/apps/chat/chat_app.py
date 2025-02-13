import functools
import json
import os
import random
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

import chainlit as cl
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import FakeListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import Field

from apps.base_app import BaseChainlitApp
from apps.handlers import AnswerCallbackHandler
from constants import LLM_PROFILES
from libs.logging_helper import logger
from services.sentinel import sentinel


def check_sentinel(args, runnable):
    """
    Check sentinel
    """
    messages: List[BaseMessage] = args["messages"]
    content_to_check = "\n".join(f"{_.content}" for _ in messages[-1:])

    passed, error_message = sentinel.validate(
        content_to_check,
        guardrails={
            "aws": {},
            "lionguard": {},
            "off-topic": {},
            "system-prompt-leakage": {},
        },
        additional_params={
            "messages": [{"content": system_prompt, "role": "system"}]
        },
    )

    if not passed:
        return ChatPromptTemplate(messages=[]) | FakeListChatModel(
            responses=[f"**WARNING**: {error_message}"]
        )

    return runnable


system_prompt = """
You are an expert chatbot in Singapore O-Level Maths, providing clear, accurate, and curriculum-aligned explanations on topics such as Algebra, Geometry, Trigonometry, and Calculus. Engage with students using step-by-step reasoning and practical examples tailored to the Singapore education system. Always ensure that interactions are respectful, unbiased, and in full compliance with community safety and moderation guidelines.
"""  # noqa: E501

EXAMPLES = json.loads(os.getenv("SENTINEL_EXAMPLES", "{}"))


class ChatApp(BaseChainlitApp):
    actions: List[str] = Field(
        default=[
            "Generate Example",
        ]
    )

    async def get_chat_settings(self, user: Optional[cl.User]):
        if not user:
            return None

        settings = [
            # cl.input_widget.Slider(
            #     id="threshold",
            #     label="Threshold for Sentinel Checks",
            #     initial=0.8,
            #     min=0,
            #     max=1,
            #     step=0.1,
            # ),
        ]

        return cl.ChatSettings(settings)

    async def on_chat_settings_update(self, settings: Dict[str, Any]):
        """Update chat settings"""
        pass

    async def on_chat_start(self):
        await cl.Message(
            content="Welcome! How can I help you with your O Level Maths today?",  # noqa: E501
        ).send()

        await self.add_message_to_memory(
            cl.Message(content=system_prompt, type="system_message"),
            check_for_edit=True,
        )

    async def setup_runnable(self):
        llm_profile = (
            next(
                p
                for p in LLM_PROFILES
                if p.name == cl.user_session.get("chat_profile")
            )
            if cl.user_session.get("chat_profile")
            else LLM_PROFILES[0]
        )

        from langchain_core.prompts import ChatPromptTemplate

        prompt = ChatPromptTemplate.from_messages(
            [
                # ("system", system_prompt),
                ("placeholder", "{messages}"),
            ]
        )

        llm = ChatOpenAI(
            model=llm_profile.default_llm_config.model,
            temperature=llm_profile.default_llm_config.temperature,
            max_tokens=llm_profile.default_llm_config.max_tokens,
            streaming=True,
        )

        runnable = (prompt | llm).with_config(
            {"run_name": cl.config.config.ui.name}
        )

        if "sentinel" in llm_profile.name.lower():
            runnable = RunnableLambda(
                functools.partial(check_sentinel, runnable=runnable)
            )

        runnable.name = llm_profile.name

        cl.user_session.set("runnable", runnable)

    async def get_runnable_input(self, message: cl.Message):
        # Limit history to last 5 messages
        return {
            "messages": self.memory.chat_memory.messages[-5:],
        }

    def get_runnable_callbacks(self) -> List[BaseCallbackHandler]:
        callbacks = super().get_runnable_callbacks()
        callbacks.append(
            AnswerCallbackHandler(
                on_message_complete=self.add_message_to_memory
            )
        )

        return callbacks

    async def on_action_taken(self, action_name: str, action: cl.Action):
        logger.info(
            {
                "msg": "Action taken",
                "action_name": action_name,
                "action": action,
            }
        )
        if action_name == "Generate Example":
            new_message = await cl.Message(
                content=random.choice(EXAMPLES.get(action.value, [])),
                type="user_message",
            ).send()
            await self.on_message(new_message)
        else:
            # Should not come here
            pass


def main():
    from chainlit.cli import run_chainlit

    cl.config.run.headless = True
    run_chainlit(__file__)


if __name__ == "__main__":
    main()

init_data = {
    "password_auth": os.getenv("ENABLE_PASSWORD_AUTH") == "true",
    "header_auth": os.getenv("ENABLE_HEADER_AUTH") == "true",
    "data_layer_type": os.getenv("CHAINLIT_DATA_LAYER", "none"),
}

logger.info(
    {
        "msg": "Setting up ChatApp",
        "init_data": init_data,
    }
)

ChatApp(**init_data).setup()
