import edge_tts
from quarter_lib.logging import setup_logging

logger = setup_logging(__file__)

VOICE_EN = "en-GB-SoniaNeural"
VOICE_DE = "de-DE-ConradNeural"


async def transcribe(text, language, filename):
	voice = VOICE_DE if language == "DE" else VOICE_EN
	communicate = edge_tts.Communicate(text, voice)
	logger.info(f"start transcription for {filename} with {voice} and {language}")
	await communicate.save(filename)
	logger.info(f"end transcription for {filename}")