import os
from typing import Literal, Optional
from openai import AsyncOpenAI

from logging_config import get_logger

logger = get_logger(__name__)

# TODO: How do i make this faster?
# TODO: Cache connection

VoiceType = Literal[
    "alloy",
    "ash",
    "ballad",
    "coral",
    "echo",
    "fable",
    "nova",
    "onyx",
    "sage",
    "shimmer",
]

AudioFormat = Literal["mp3"]


async def convert_text_to_speech(
    text: str,
    voice: VoiceType = "coral",
    model: str = "gpt-4o-mini-tts",
    response_format: AudioFormat = "mp3",
    instructions: Optional[str] = None,
) -> bytes:
    """
    Convert text to speech using OpenAI TTS API.

    Args:
        text: The text to convert to speech
        voice: The voice to use (default: coral)
        model: The TTS model to use (default: gpt-4o-mini-tts)
        response_format: Audio format (default: mp3)
        instructions: Optional instructions for how to speak (e.g., "Speak in a cheerful and positive tone")

    Returns:
        bytes: Audio data

    Raises:
        ValueError: If OPENAI_API_KEY is not set
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    try:
        client = AsyncOpenAI(api_key=api_key)

        logger.debug(
            f"Converting text to speech: voice={voice}, format={response_format}, length={len(text)} chars"
        )

        if instructions:
            response = await client.audio.speech.create(
                model=model,
                voice=voice,
                input=text,
                response_format=response_format,
                instructions=instructions,
            )
        else:
            response = await client.audio.speech.create(
                model=model, voice=voice, input=text, response_format=response_format
            )

        audio_bytes = response.content

        logger.debug(
            f"Text-to-speech completed: {len(text)} chars → {len(audio_bytes)} bytes"
        )

        return audio_bytes

    except Exception as e:
        logger.error(f"Error converting text to speech: {str(e)}")
        raise


async def convert_summary_to_speech(
    summary_data: dict, voice: VoiceType = "coral", response_format: AudioFormat = "mp3"
) -> bytes:
    """
    Convert an LLM summary to speech for anxious driver guidance.

    Extracts the summary text from the LLM response and converts it to audio.

    Args:
        summary_data: Dictionary containing LLM summary with 'summary' field
        voice: The voice to use
        response_format: Audio format

    Returns:
        bytes: Audio data
    """
    summary_text = summary_data.get("summary", "")

    if not summary_text:
        raise ValueError("No summary text found in LLM response")

    instructions = "Speak in a clear, professional, informative tone. Use a steady, measured pace suitable for delivering detailed information. Be thorough and methodical, ensuring every detail is communicated clearly. This is comprehensive street information, not a conversation."

    return await convert_text_to_speech(
        text=summary_text,
        voice=voice,
        response_format=response_format,
        instructions=instructions,
    )
