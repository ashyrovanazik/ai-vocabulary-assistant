import os
import json
import re
import requests


LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-plus")
LLM_MODEL_MAX_TOKENS = int(os.getenv("LLM_MODEL_MAX_TOKENS", "800"))
print("API KEY =", LLM_API_KEY)
print("BASE URL =", LLM_BASE_URL)
print("MODEL =", LLM_MODEL)
print("MAX TOKENS =", LLM_MODEL_MAX_TOKENS)

def generate_prompt(word, example_sentence):
    return f"""
You are an English vocabulary tutor.

Analyze the English word: "{word}"

Context sentence:
"{example_sentence}"

Return ONLY valid JSON.

Required format:
{{
  "word": "{word}",
  "phonetic": "",
  "part_of_speech": "",
  "chinese_meaning": "",
  "pinyin": "",
  "definition": "",
  "collocations": "",
  "synonyms": "",
  "antonyms": "",
  "chinese_translation": "",
  "difficulty": "",
  "ai_explanation": ""
}}

Rules:
- phonetic must be IPA
- chinese_meaning must be Chinese
- pinyin must be the standard pinyin of chinese_meaning with tone marks
- definition must be English
- chinese_translation must translate the context sentence into Chinese
- collocations must be comma separated
- synonyms must be comma separated
- antonyms must be comma separated
- difficulty must be Beginner, Intermediate, or Advanced
- ai_explanation must explain the word in simple English
- return JSON only
- do not use markdown
- do not use ```json
- do not add comments
"""


def clean_json_text(text):
    text = text.strip()

    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start:end + 1]

    return text


def generate_word_data(word, example_sentence):
    if not LLM_API_KEY:
        return fallback_word_data(word, example_sentence, "LLM_API_KEY not found")

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": generate_prompt(word, example_sentence)
            }
        ],
        "temperature": 0.2,
        "max_tokens": LLM_MODEL_MAX_TOKENS
    }

    try:
        response = requests.post(
            LLM_BASE_URL,
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        cleaned = clean_json_text(content)

        data = json.loads(cleaned)

        return {
            "word": data.get("word", word),
            "phonetic": data.get("phonetic", ""),
            "part_of_speech": data.get("part_of_speech", ""),
            "chinese_meaning": data.get("chinese_meaning", ""),
            "pinyin": data.get("pinyin", ""),
            "definition": data.get("definition", ""),
            "collocations": data.get("collocations", ""),
            "synonyms": data.get("synonyms", ""),
            "antonyms": data.get("antonyms", ""),
            "chinese_translation": data.get("chinese_translation", ""),
            "difficulty": data.get("difficulty", "Intermediate"),
            "ai_explanation": data.get("ai_explanation", "")
        }

    except Exception as e:
        print("LLM ERROR:", e)
        return fallback_word_data(word, example_sentence, str(e))


def fallback_word_data(word, example_sentence, reason=""):
    return {
        "word": word,
        "phonetic": "",
        "part_of_speech": "",
        "chinese_meaning": "",
        "pinyin": "",
        "definition": example_sentence or "",
        "collocations": "",
        "synonyms": "",
        "antonyms": "",
        "chinese_translation": "",
        "difficulty": "Intermediate",
        "ai_explanation": f"Fallback response used. Reason: {reason}"
    }