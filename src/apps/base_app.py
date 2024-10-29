import logging
import os
import time
import uuid
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List
from typing import Literal
from typing import Optional

import chainlit as cl
import uvicorn
from chainlit import User
from chainlit.utils import mount_chainlit
from fastapi import Response
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_memory import BaseChatMemory
from langchain_community.llms.fake import FakeListLLM
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable
from langchain_core.runnables import RunnableConfig
from pydantic.v1 import BaseModel
from pydantic.v1 import Field
from starlette.datastructures import Headers

from constants import LLM_PROFILES
from libs import cryptography_helper
from libs.logging_helper import logger

cl_to_langchain_msg_type_map = {
    "user_message": HumanMessage,
    "assistant_message": AIMessage,
    "system_message": SystemMessage,
}

LOADING_IMAGE = """![loading](/public/images/loading/4.svg "loading")"""


class BaseChainlitApp(BaseModel):
    """Base Chainlit App that uses streaming"""

    data_layer_type: Literal["sqlalchemy", "none"] = Field(default="none")
    """Data Layer type"""
    password_auth: bool = Field(default=False)
    """Enable password authentication"""
    header_auth: bool = Field(default=False)
    """Enable header-based authentication"""
    support_chat_resume: bool = Field(default=False)
    """Whether this app support resuming a chat"""
    actions: List[str] = Field(default=[])
    """List of action names that this app support"""

    names_in_stream_events: List[str] = Field(
        default=[
            cl.config.config.ui.name,
            f"_{cl.config.config.ui.name}",
            FakeListLLM.__name__,
        ]
    )

    def setup(self):
        """Hook up Chainlit events while allowing subclass to override"""

        if self.data_layer_type == "sqlalchemy":
            from chainlit.data.sql_alchemy import SQLAlchemyDataLayer

            cl.data._data_layer = SQLAlchemyDataLayer(
                conninfo=os.environ["CHAINLIT_DB_CONNECTION"],
                ssl_require=os.getenv("CHAINLIT_DB_REQUIRE_SSL", "false")
                == "true",
            )

        if self.password_auth:
            cl.password_auth_callback(self.password_auth_callback)

        if self.header_auth:
            cl.header_auth_callback(self.header_auth_callback)

        cl.on_logout(self.on_logout)

        cl.set_starters(self.get_conversation_starters)

        @cl.set_chat_profiles
        async def chat_profiles(user: Optional[User]):
            return await self.chat_profiles(user)

        @cl.on_chat_start
        async def on_chat_start():
            """Add conversation memory to session before runnable setup"""

            cl.user_session.set(
                "memory", ConversationBufferMemory(return_messages=True)
            )

            await self.setup_runnable()

            await self.on_chat_start()

            if settings := await self.get_chat_settings(
                cl.user_session.get("user")
            ):
                await settings.send()
                cl.on_settings_update(self.on_chat_settings_update)

        async def on_chat_resume(thread: cl.types.ThreadDict):
            memory: BaseChatMemory = ConversationBufferMemory(
                return_messages=True,
                chat_memory=InMemoryChatMessageHistory(
                    messages=[
                        cl_to_langchain_msg_type_map[message["type"]](
                            content=message["output"],
                            additional_kwargs={"id": message["id"]},
                        )
                        for message in thread["steps"]
                        if message["type"] in cl_to_langchain_msg_type_map
                        and message["output"] != ""
                    ]
                ),
            )

            # Remove any empty message from the UI
            for message in thread["steps"]:
                if (
                    message["type"] in cl_to_langchain_msg_type_map
                    and message["output"] == ""
                ):
                    await cl.Message(id=message["id"], content="").remove()

            cl.user_session.set("memory", memory)

            await self.setup_runnable()

            await self.on_chat_resume(thread)

        if self.support_chat_resume:
            cl.on_chat_resume(on_chat_resume)

        @cl.on_message
        async def on_message(message: cl.Message):
            tags: List[str] = []
            metadata: Dict[str, str] = {}

            user = cl.user_session.get("user")
            if user and hasattr(user, "id"):
                metadata["user_id"] = user.id

            return await self.on_message(
                message, langsmith_extra={"tags": tags, "metadata": metadata}
            )

        for action_name in self.actions:

            @cl.action_callback(action_name)
            async def on_action_taken(action: cl.Action):
                await self.on_action_taken(action.name, action)

    async def password_auth_callback(self, username: str, password: str):
        if os.getenv("CHAINLIT_PWD_USERS"):
            pwd_users = os.getenv("CHAINLIT_PWD_USERS", "").split(";")
            hashed_pw = cryptography_helper.hash(password)
            if f"{username}:{hashed_pw}" in pwd_users:
                if username == "pwd_bypass_usr":
                    return cl.User(
                        identifier=f"{username} {str(uuid.uuid4())[:8]}",
                        metadata={"role": username, "provider": "credentials"},
                    )

                return cl.User(
                    identifier=username,
                    metadata={"role": "user", "provider": "credentials"},
                )
        return None

    async def header_auth_callback(
        self, headers: Headers
    ) -> Optional[cl.User]:

        return None

    def on_logout(self, _, response: Response):
        return {"success": True}

    @property
    def memory(self) -> BaseChatMemory:
        return cl.user_session.get("memory")

    async def add_message_to_memory(
        self, message: cl.Message, check_for_edit: bool = False, **kwargs
    ):
        logger.info(
            {"msg": "Adding message to history", "message_id": message.id}
        )
        if not (
            message_type := cl_to_langchain_msg_type_map.get(message.type)
        ):
            raise ValueError(f"Invalid message type: {message.type}")

        if check_for_edit:
            messages: List[BaseMessage] = []
            for history_message in self.memory.chat_memory.messages:
                if history_message.additional_kwargs.get("id") == message.id:
                    # Message already exists in history,
                    # so this must be a user-edited message.
                    # In this case we need to remove the remaining messages

                    self.memory.chat_memory.messages = messages
                    break

                messages.append(history_message)

        # check if the last message in memory is empty, if so, remove it
        if (
            self.memory.chat_memory.messages
            and self.memory.chat_memory.messages[-1].content == ""
        ):
            removed_message = self.memory.chat_memory.messages.pop()

            await cl.Message(
                id=removed_message.additional_kwargs.get("id"), content=""
            ).remove()

        kwargs["id"] = message.id

        self.memory.chat_memory.add_message(
            message_type(content=message.content, additional_kwargs=kwargs)
        )

    async def get_conversation_starters(
        self, user: Optional[User]
    ) -> List[cl.Starter]:
        return []

    @abstractmethod
    async def on_chat_start(self):
        """Subclass need to implement this"""

    @abstractmethod
    async def setup_runnable(self):
        """Subclass need to implement this"""

    async def on_chat_resume(self, thread: cl.types.ThreadDict):
        """Subclass need to override this if resuming chat is supported"""
        pass

    async def get_chat_settings(
        self, user: Optional[cl.User]
    ) -> Optional[cl.ChatSettings]:
        """Get chat settings"""
        return None

    async def on_chat_settings_update(self, settings: Dict[str, Any]):
        """Update chat settings"""
        pass

    async def on_message(self, message: cl.Message, **kwargs):
        """Default implementation using runnable and streaming"""
        start_time = time.time()
        logger.info(
            {
                "msg": "Received new user message",
                **(
                    {"message": message.content}
                    if logger.level == logging.DEBUG
                    else {}
                ),
            }
        )
        await self.add_message_to_memory(message, check_for_edit=True)

        waiting_message = await self.get_waiting_message().send()
        cl.user_session.set("waiting_message", waiting_message)

        runnable: Runnable = cl.user_session.get("runnable")
        # cb = cl.AsyncLangchainCallbackHandler(stream_final_answer=True)
        callbacks = self.get_runnable_callbacks()

        runnable_input = await self.get_runnable_input(message)

        # Just invoke the runnable here and let the callbacks handle results
        try:
            # await runnable.ainvoke(runnable_input, callbacks=callbacks)
            async for event in runnable.astream_events(
                runnable_input,
                version="v2",
                config=RunnableConfig(callbacks=callbacks),
                include_names=self.names_in_stream_events,
            ):
                logger.debug(
                    {
                        "msg": "Streaming event",
                        "event_type": event["event"],
                        "name": event["name"],
                        # "data": event["data"],
                    }
                )
        except Exception as e:
            error_id = str(uuid.uuid4())[:8]
            logger.error(
                {
                    "msg": "Error while handling new user message",
                    "error": str(e),
                    "error_id": error_id,
                }
            )
            unknown_error_text = (
                "Apologies, something went wrong. "
                "Please try again later. Error id:"
            )
            await cl.Message(
                f"{unknown_error_text} {error_id}",
                type="system_message",
            ).send()
        finally:
            await cl.user_session.get("waiting_message").remove()
            cl.user_session.set("waiting_message", None)

        logger.info(
            {
                "msg": "Finish handling user message",
                "time_taken": time.time() - start_time,
            }
        )

    @classmethod
    def get_waiting_message(cls) -> cl.Message:
        return cl.Message(LOADING_IMAGE)

    async def chat_profiles(self, user: Optional[User]):
        """Use LLM profiles from LLM_PROFILES environment variable"""
        return [
            cl.ChatProfile(
                name=profile.name,
                markdown_description=profile.description,
                icon=profile.icon,
            )
            for profile in LLM_PROFILES
        ]

    @abstractmethod
    async def get_runnable_input(self, message: cl.Message):
        """Get the input used to pass to runnable,
        each subclass needs to provide its own parameters"""

    def get_runnable_callbacks(self) -> List[BaseCallbackHandler]:
        """
        Return a list of callbacks used when running a runnable.

        This method should be overridden in subclasses if a custom callback
        is needed.

        Returns:
            List of callbacks.
        """
        callbacks = [cl.AsyncLangchainCallbackHandler()]
        try:
            if os.getenv("LANGFUSE_SECRET_KEY"):
                from langfuse.callback import CallbackHandler

                callbacks.append(CallbackHandler())
        except Exception:
            pass

        return callbacks

    async def send_message(self, message: cl.Message, **kwargs):
        """ Send the message to user and record it in memory
        :param message: The message to send
        :param kwargs: Additional kwargs to save in memory
        """ ""
        await message.send()
        await self.add_message_to_memory(message, **kwargs)

    async def on_action_taken(self, action_name: str, action: cl.Action):
        pass


def run_chainlit_app(chainlit_file: str, path: str, origins: List[str]):
    host = os.environ.get("CHAINLIT_HOST", "0.0.0.0")
    port = int(os.environ.get("CHAINLIT_PORT", "8000"))

    print(
        f"Visit http://{host}:{port}/public/copilot_test.html for copilot test"
    )
    print(f"Visit http://{host}:{port}{path}/ for chat bot")

    from fastapi import FastAPI, status
    from fastapi.responses import RedirectResponse
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/public", StaticFiles(directory="public"), name="public")
    app.get("/")(
        lambda: RedirectResponse(url=path, status_code=status.HTTP_302_FOUND)
    )

    mount_chainlit(app=app, target=chainlit_file, path=path)

    # run_chainlit(__file__)

    uvicorn.run(
        app,
        host=host,
        port=port,
        # reload=True,
    )
