import functools
import os
from typing import List

import chainlit as cl
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.language_models import FakeListChatModel
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI

from apps.base_app import BaseChainlitApp
from apps.handlers import AnswerCallbackHandler
from constants import LLM_PROFILES
from libs.logging_helper import logger
from services.sentinel.main import call_sentinel_api


def check_sentinel(args, runnable):
    """
    Check sentinel

    # Sample output
    {
      "outputs": {
        "lionguard": {
          "binary": 0,
          "hateful": 0,
          "harassment": 0,
          "public_harm": 0,
          "self_harm": 0,
          "sexual": 0,
          "toxic": 0,
          "violent": 0
        },
        "promptguard": {
          "jailbreak": 0.9804580807685852
        },
        "off-topic-2": {
          "off-topic": 0.28574493527412415
        },
        "request_id": "1f8e8089-b71b-4054-881b-ee727f46f3c2"
      }
    }

    """
    messages: List[BaseMessage] = args["messages"]
    content_to_check = "\n".join(
        f"{_.type}: {_.content}" for _ in messages[-3:]
    )

    sentinel_check_result = call_sentinel_api(
        content_to_check,
        filters=["lionguard", "promptguard"],
    )

    sentinel_checks = [
        {
            "type": "promptguard",
            "subtype": "jailbreak",
            "threshold": 0.8,
            "message": "Jailbreak attempt detected and logged.",
        },
        {
            "type": "off-topic-2",
            "subtype": "off-topic",
            "threshold": 0.8,
            "message": "Off-topic message detected and logged.",
        },
        # {
        #     "type": "lionguard",
        #     "subtype": "binary",
        #     "threshold": 0.8,
        #     "message": "Binary message detected and logged.",
        # },
        {
            "type": "lionguard",
            "subtype": "hateful",
            "threshold": 0.8,
            "message": "Hateful message detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "harassment",
            "threshold": 0.8,
            "message": "Harassment detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "public_harm",
            "threshold": 0.8,
            "message": "Public harm detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "self_harm",
            "threshold": 0.8,
            "message": "Self harm detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "sexual",
            "threshold": 0.8,
            "message": "Sexual content detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "toxic",
            "threshold": 0.8,
            "message": "Toxic content detected and logged.",
        },
        {
            "type": "lionguard",
            "subtype": "violent",
            "threshold": 0.8,
            "message": "Violent content detected and logged.",
        },
    ]

    for check in sentinel_checks:
        if (
            sentinel_check_result["outputs"]
            .get(check["type"], {})
            .get(check["subtype"], 0)
            > check["threshold"]
        ):
            return ChatPromptTemplate(messages=[]) | FakeListChatModel(
                responses=[f'WARNING: {check["message"]}']
            )

    return runnable


system_prompt = (
    "You are a chatbot specialised in providing dates related to "
    "Singapore history. "
    "Do not answer any questions that are not related to dates."
)


class ChatApp(BaseChainlitApp):
    async def on_chat_start(self):
        await cl.Message(
            content="Welcome! I specialised in providing dates related to "
            "Singapore history."
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
                ("system", system_prompt),
                ("placeholder", "{messages}"),
            ]
        )

        llm = ChatOpenAI(
            model_name=(
                "gpt-4o-mini-prd-gcc2-lb"
                if llm_profile.default_llm_config.model.startswith(
                    "gpt-4o-mini"
                )
                else "gpt-4o-prd-gcc2-lb"
            ),
            temperature=llm_profile.default_llm_config.temperature,
            max_tokens=llm_profile.default_llm_config.max_tokens,
            streaming=True,
        )

        runnable = (prompt | llm).with_config(
            {"run_name": cl.config.config.ui.name}
        )

        if "sentinel" in llm_profile.name:
            runnable = RunnableLambda(
                functools.partial(check_sentinel, runnable=runnable)
            )

        cl.user_session.set("runnable", runnable)

    async def get_runnable_input(self, message: cl.Message):
        # Limit history to last 5 messages
        return {
            "messages": self.memory.chat_memory.messages[-5:],
        }

    def get_runnable_callbacks(self) -> List[BaseCallbackHandler]:
        callbacks = super().get_runnable_callbacks()
        callbacks.append(AnswerCallbackHandler())

        return callbacks


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
