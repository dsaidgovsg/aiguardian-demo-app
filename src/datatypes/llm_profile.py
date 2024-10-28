from typing import Optional

from pydantic import BaseModel

from datatypes.llm_config import LLMConfig


class LLMProfile(BaseModel):
    name: str
    description: str
    icon: Optional[str] = None
    default_llm_config: LLMConfig
