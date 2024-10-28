from langchain.load.serializable import Serializable


class LLMConfig(Serializable):
    provider: str = "openai"
    model: str
    temperature: float | None = 0.7
    max_tokens: int | None = None

    def __repr__(self):
        return (
            f"LLMConfig(provider='{self.provider}', "
            f"model='{self.model}', "
            f"temperature={self.temperature}, "
            f"max_tokens={self.max_tokens})"
        )
