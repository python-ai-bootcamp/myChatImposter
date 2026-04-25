from media_processors.error_processors import CorruptMediaProcessor, UnsupportedMediaProcessor
from media_processors.stub_processors import (
    DocumentProcessor,
    VideoDescriptionProcessor,
)
from media_processors.audio_transcription_processor import AudioTranscriptionProcessor
from media_processors.image_vision_processor import ImageVisionProcessor


PROCESSOR_CLASS_MAP = {
    "AudioTranscriptionProcessor": AudioTranscriptionProcessor,
    "VideoDescriptionProcessor": VideoDescriptionProcessor,
    "ImageVisionProcessor": ImageVisionProcessor,
    "DocumentProcessor": DocumentProcessor,
    "CorruptMediaProcessor": CorruptMediaProcessor,
    "UnsupportedMediaProcessor": UnsupportedMediaProcessor,
}


def get_processor_class(class_name: str):
    if class_name not in PROCESSOR_CLASS_MAP:
        raise ValueError(f"Unknown processor class: {class_name}")
    return PROCESSOR_CLASS_MAP[class_name]
