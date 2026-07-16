import asyncio
import edge_tts

VOICE_LIST = []

def load_voices_sync():
    global VOICE_LIST
    if not VOICE_LIST:
        try:
            print("Fetching Microsoft Edge TTS voices list...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(edge_tts.VoicesManager.create())
            VOICE_LIST = voices.voices
            if not VOICE_LIST:
                raise ValueError("Empty voices list returned from Edge TTS")
            loop.close()
            print(f"Loaded {len(VOICE_LIST)} voices from Microsoft Edge TTS.")
        except Exception as e:
            print(f"Error fetching Edge TTS voices: {e}. Using fallback voice list.")
            VOICE_LIST = [
                {"ShortName": "en-US-AriaNeural", "Locale": "en-US", "Gender": "Female"},
                {"ShortName": "en-US-GuyNeural", "Locale": "en-US", "Gender": "Male"},
                {"ShortName": "es-ES-ElviraNeural", "Locale": "es-ES", "Gender": "Female"},
                {"ShortName": "es-ES-AlvaroNeural", "Locale": "es-ES", "Gender": "Male"},
                {"ShortName": "fr-FR-DeniseNeural", "Locale": "fr-FR", "Gender": "Female"},
                {"ShortName": "fr-FR-HenriNeural", "Locale": "fr-FR", "Gender": "Male"},
                {"ShortName": "de-DE-AmalaNeural", "Locale": "de-DE", "Gender": "Female"},
                {"ShortName": "de-DE-ConradNeural", "Locale": "de-DE", "Gender": "Male"},
                {"ShortName": "zh-CN-XiaoxiaoNeural", "Locale": "zh-CN", "Gender": "Female"},
                {"ShortName": "zh-CN-YunxiNeural", "Locale": "zh-CN", "Gender": "Male"},
                {"ShortName": "ja-JP-NanamiNeural", "Locale": "ja-JP", "Gender": "Female"},
                {"ShortName": "ja-JP-KeitaNeural", "Locale": "ja-JP", "Gender": "Male"},
                {"ShortName": "km-KH-SreymomNeural", "Locale": "km-KH", "Gender": "Female"},
                {"ShortName": "km-KH-PisethNeural", "Locale": "km-KH", "Gender": "Male"},
            ]
    return VOICE_LIST

async def synthesize_text_async(text, voice, output_path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def generate_tts(text, voice, output_path):
    try:
        asyncio.run(synthesize_text_async(text, voice, output_path))
        return True
    except Exception as e:
        print(f"TTS Synthesis error for text '{text}': {e}")
        return False
