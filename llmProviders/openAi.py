from langchain_openai import ChatOpenAI

class LlmProvider:
    def __init__(self, config: dict, user_id: str):
        self.config = config
        self.user_id = user_id

    def get_llm(self):
        # The ChatOpenAI client will automatically use the OPENAI_API_KEY environment variable
        # if the api_key argument is not provided. We will pass all config keys to the constructor
        # and let it pick the ones it needs. This makes the provider flexible.

        # We need to separate the system prompt from the LLM parameters.
        llm_params = self.config.copy()
        llm_params.pop("system", None)

        return ChatOpenAI(**llm_params)

    def get_system_prompt(self):
        system_prompt = self.config.get("system", "You are a helpful assistant.")
        # I will assume a placeholder {user_id} and format it.
        return system_prompt.format(user_id=self.user_id)
