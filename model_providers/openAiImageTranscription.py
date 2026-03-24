from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

from .image_transcription import ImageTranscriptionProvider
from .openAi import OpenAiMixin
from config_models import ImageTranscriptionProviderConfig


class OpenAiImageTranscriptionProvider(ImageTranscriptionProvider, OpenAiMixin):
    """Concrete OpenAI-based image transcription provider.
    
    Uses constructor-time ChatOpenAI initialization. The `detail` parameter is
    popped from llm_params (it is transcription-only metadata and must never be
    forwarded to ChatOpenAI). No model/detail compatibility validation is added
    — this is an accepted, deliberate design choice per spec.
    """
    def __init__(self, config: ImageTranscriptionProviderConfig):
        super().__init__(config)
        params = self._build_llm_params()
        self._detail = params.pop("detail", "auto")
        self._llm = ChatOpenAI(**params)

    def get_llm(self):
        return self._llm

    async def transcribe_image(self, base64_image: str, mime_type: str, language_code: str) -> str:
        """Transcribe an image using a multimodal HumanMessage.
        
        Constructs a prompt with the language_code, sends the base64 image via
        data URI, and normalizes the response per the three-branch contract.
        """
        prompt_text = (
            f"Describe the contents of this image explicitly in the following language: "
            f"{language_code}, and concisely in 1-3 sentences. If there is text in the "
            f"image, add the text inside image to description as well."
        )
        
        data_uri = f"data:{mime_type};base64,{base64_image}"
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": data_uri,
                        "detail": self._detail,
                    },
                },
            ]
        )
        
        response = await self._llm.ainvoke([message])
        
        # Normalize response per the three-branch contract:
        # 1. If response.content is str: return as-is
        # 2. If response.content is content blocks: extract text-bearing blocks and concatenate
        # 3. Otherwise: return fallback string
        return self._normalize_response(response.content)

    @staticmethod
    def _normalize_response(content) -> str:
        """Normalize the LLM response content to a plain string.
        
        - str → returned as-is
        - list of content blocks → extract text-bearing blocks, concatenate with 
          single-space separator, trim outer whitespace
        - anything else → fallback string
        """
        if isinstance(content, str):
            return content
        
        if isinstance(content, list):
            text_parts = []
            for block in content:
                if isinstance(block, str):
                    text_parts.append(block)
                elif isinstance(block, dict) and "text" in block:
                    text_parts.append(block["text"])
                elif hasattr(block, "text"):
                    text_parts.append(block.text)
            if text_parts:
                return " ".join(text_parts).strip()
        
        return "Unable to transcribe image content"
