from deep_translator import GoogleTranslator

def translate_text(text, source_lang="auto", target_lang="es"):
    if not text.strip():
        return ""
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        return translator.translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text
