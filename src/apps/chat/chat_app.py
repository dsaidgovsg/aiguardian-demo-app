import os
from typing import List

import chainlit as cl
from langchain_core.callbacks import BaseCallbackHandler

from apps.base_app import BaseChainlitApp
from apps.handlers import AnswerCallbackHandler
from libs.logging_helper import logger


class ChatApp(BaseChainlitApp):
    async def on_chat_start(self):
        pass

    async def setup_runnable(self):
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.language_models import GenericFakeChatModel

        prompt = ChatPromptTemplate.from_messages(
            [("system", "You are a chatbot."), ("placeholder", "{messages}")]
        )

        llm = GenericFakeChatModel(
            messages=iter(
                [
                    "I'm a bot powered by "
                    + cl.user_session.get("chat_profile"),
                    "I'll keep repeating the above",
                ]
            ),
        )

        runnable = (prompt | llm).with_config(
            {"run_name": cl.config.config.ui.name}
        )

        cl.user_session.set("runnable", runnable)

    async def get_runnable_input(self, message: cl.Message):
        return {
            "messages": self.memory.chat_memory.messages,
        }

    def get_runnable_callbacks(self) -> List[BaseCallbackHandler]:
        return [
            cl.AsyncLangchainCallbackHandler(),
            AnswerCallbackHandler(),
        ]


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
