"""AI Tutor — an English → Hong Kong Cantonese speaking coach.

A Python port of the ``AI_tutor/`` project (React + Hono). It brings the three
tutor personas, the eight scenario packs, the strict-JSON Lesson Agent prompt,
and a scripted fallback (degradation contract) into a single Streamlit tab.

Design (kept from the PRD):
  * speak/type English → tutor returns a short colloquial Cantonese reply with
    Jyutping + English + an optional correction + a "next try" prompt,
  * replies are 1–2 sentences (speed), Traditional Chinese + LSHK Jyutping
    (accuracy), and never invent vocabulary (honesty),
  * if the LLM is unavailable we fall back to a scripted reply so the tab still
    works (uptime).

Speed/quality/accuracy improvements over the raw TS port:
  * replies capped (max_tokens), temperature 0, single JSON call,
  * Jyutping is validated with ``app/jyutping_validate`` and flagged when wrong,
  * saved phrases are kept locally (SM-2-lite) for review.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import config

# --------------------------------------------------------------------------- #
# Personas (ported from AI_tutor/app/contracts/personas.ts)
# --------------------------------------------------------------------------- #
PERSONAS = [
    {
        "id": "wing", "name": "Ah Wing", "cantonese": "阿Wing", "avatar": "🧑‍🎤",
        "role": "Your practice buddy",
        "style": "Casual, encouraging, loves board games and hotpot",
        "prompt": "You are Ah Wing, a 26-year-old Hong Konger. Casual, playful, "
                 "encouraging. You love hotpot, hiking and board games. You use "
                 "light slang (正, 好嘢, 唔錯) and particles naturally (呀, 㗎, 喎, 啲).",
        "intro": {
            "cantonese": "哈囉！我係阿Wing，你嘅廣東話練習朋友。準備好未？",
            "jyutping": "haa1 lou3! ngo5 hai6 aa3 Wing, nei5 ge3 gwong2 dung1 "
                        "waa2 lin6 zaap6 pang4 jau5. zeon2 bei6 hou2 mei6?",
            "english": "Hey! I'm Ah Wing, your Cantonese practice buddy. Ready?",
        },
    },
    {
        "id": "chantai", "name": "Mrs Chan", "cantonese": "陳太", "avatar": "👩‍🦱",
        "role": "Patient neighbour",
        "style": "Warm, patient, speaks slowly and clearly",
        "prompt": "You are Mrs Chan, a warm, patient neighbour in her 50s. You "
                 "speak slowly and clearly, use simple vocabulary, and always "
                 "praise effort before correcting. You never rush the learner.",
        "intro": {
            "cantonese": "你好呀，我係陳太。慢慢嚟，唔使急，我哋一句一句練。",
            "jyutping": "nei5 hou2 aa3, ngo5 hai6 can4 taai3. maan6 maan2 lai4, "
                        "m4 sai1 gap1, ngo5 dei6 jat1 geoi3 jat1 geoi3 lin6.",
            "english": "Hello, I'm Mrs Chan. Take it slow, no rush — we'll "
                       "practise sentence by sentence.",
        },
    },
    {
        "id": "haajie", "name": "Ha Jeh", "cantonese": "霞姐", "avatar": "👩‍🍳",
        "role": "Cha chaan teng veteran",
        "style": "Fast-talking, witty, teaches real street Cantonese",
        "prompt": "You are Ha Jeh, a witty, fast-talking cha chaan teng worker "
                 "with 20 years of experience. You teach real street Cantonese: "
                 "埋單, 走冰, 搭枱, 飛沙走奶. You tease gently but are kind.",
        "intro": {
            "cantonese": "喂！我係霞姐。想學地道廣東話？跟我落單就啱啦！",
            "jyutping": "wai3! ngo5 hai6 haa4 ze1. soeng2 hok6 dei6 dou6 gwong2 "
                        "dung1 waa2? gan1 ngo5 lok6 daan1 zau6 ngaam3 laa1!",
            "english": "Hey! I'm Ha Jeh. Want to learn real street Cantonese? "
                       "Just follow my lead!",
        },
    },
]


def get_persona(pid: str | None) -> dict:
    return next((p for p in PERSONAS if p["id"] == pid), PERSONAS[0])


# --------------------------------------------------------------------------- #
# Scenarios (8 = 7 guided + free talk; ported from contracts/scenarios.ts)
# --------------------------------------------------------------------------- #
SCENARIOS = [
    {"id": "greetings", "title": "Greetings & Introductions",
     "subtitle": "Say hello, introduce yourself, small talk", "icon": "👋",
     "setting": "Meeting a neighbour in your building lobby in Hong Kong.",
     "objectives": ["Greet by time of day", "Introduce name + origin",
                    "Ask/answer how someone is", "Use 唔該 vs 多謝 correctly"],
     "phrases": [
        {"cantonese": "早晨！", "jyutping": "zou2 san4!", "english": "Good morning!"},
        {"cantonese": "你好，我叫 Alex。", "jyutping": "nei5 hou2, ngo5 giu3 Alex.",
         "english": "Hello, my name is Alex."},
        {"cantonese": "我係美國人。", "jyutping": "ngo5 hai6 mei5 gwok3 jan4.",
         "english": "I am American."},
        {"cantonese": "你近排點呀？", "jyutping": "nei5 gan6 paai4 dim2 aa3?",
         "english": "How have you been lately?"},
        {"cantonese": "幾好呀，多謝！", "jyutping": "gei2 hou2 aa3, do1 ze6!",
         "english": "Pretty good, thanks!"},
        {"cantonese": "好高興認識你。", "jyutping": "hou2 gou1 hing3 jing6 sik1 nei5.",
         "english": "Nice to meet you."},
        {"cantonese": "你識唔識講英文？", "jyutping": "nei5 sik1 m4 sik1 gong2 jing1 man2?",
         "english": "Can you speak English?"},
        {"cantonese": "遲啲見，拜拜！", "jyutping": "ci4 di1 gin3, baai1 baai3!",
         "english": "See you later, bye!"},
     ]},
    {"id": "cha-chaan-teng", "title": "Ordering at a Cha Chaan Teng",
     "subtitle": "Milk tea, ordering, asking for the bill", "icon": "🍽️",
     "setting": "A bustling cha chaan teng (Hong Kong café) at lunch time.",
     "objectives": ["Order food/drinks", "Ask for the bill (埋單)", "Use 走冰 / 飛沙走奶"],
     "phrases": []},
    {"id": "transport", "title": "MTR, Taxis & Directions",
     "subtitle": "Getting around Hong Kong without panic", "icon": "🚇",
     "setting": "You're heading to Mong Kok and need directions, then a taxi.",
     "objectives": ["Ask for directions", "Give a destination", "Understand replies"],
     "phrases": []},
    {"id": "shopping", "title": "Shopping & Payments",
     "subtitle": "Bargaining, sizes, and paying", "icon": "🛍️",
     "setting": "A clothing shop at a market in Causeway Bay.",
     "objectives": ["Ask price/size", "Bargain politely", "Pay (card/Octopus)"],
     "phrases": []},
    {"id": "workplace", "title": "Workplace Small Talk",
     "subtitle": "Office chat, meetings, after-work plans", "icon": "💼",
     "setting": "Monday morning at the office pantry with your colleague Ka Yan.",
     "objectives": ["Greet colleagues", "Small talk", "Make after-work plans"],
     "phrases": []},
    {"id": "social", "title": "Making Friends & Social Talk",
     "subtitle": "Hobbies, plans, hotpot invitations", "icon": "🎲",
     "setting": "You meet a new friend, Wing, at a board-game night in Sheung Wan.",
     "objectives": ["Talk about hobbies", "Invite someone out", "Accept/decline plans"],
     "phrases": []},
    {"id": "emergency", "title": "Emergency & Medical Basics",
     "subtitle": "Getting help, seeing a doctor, pharmacy", "icon": "🏥",
     "setting": "You feel unwell and need to see a doctor in Hong Kong.",
     "objectives": ["Say you are unwell", "Describe symptoms", "Ask for help/medicine"],
     "phrases": []},
    {"id": "free-talk", "title": "Free Talk",
     "subtitle": "No script — talk about anything, in any mix", "icon": "💬",
     "setting": "An open conversation with your tutor persona — your day, interests, anything.",
     "objectives": ["Have a natural conversation"], "phrases": []},
]


def get_scenario(sid: str | None) -> dict:
    return next((s for s in SCENARIOS if s["id"] == sid), SCENARIOS[0])


# --------------------------------------------------------------------------- #
# Lesson Agent prompt (ported from AI_tutor/app/api/prompts.ts, condensed)
# --------------------------------------------------------------------------- #
TUTOR_SYSTEM = (
    "You are \"Real AI Tutor,\" a friendly Hong Kong Cantonese speaking coach for "
    "an English-speaking learner. Rules:\n"
    "1. Reply in natural colloquial Hong Kong Cantonese, 1-2 short sentences.\n"
    "2. If the learner writes English, give a natural Cantonese version of what "
    "they need to say (cantonese_reply), then continue the roleplay in it.\n"
    "3. If the learner writes Cantonese, reply in Cantonese and gently correct "
    "only the most important error.\n"
    "4. Use Traditional Chinese + accurate LSHK Jyutping (tone 1-6) for all "
    "Cantonese. Never use Mandarin vocab/patterns (係 not 是, 唔 not 不, 嘅 not 的, "
    "喺 not 在, 咗 not 了, 咩 not 嗎, 鍾意 not 喜歡).\n"
    "5. If unsure of an expression, say so — do not invent.\n"
    "6. Output STRICT JSON only: {\"cantonese_reply\":str, \"jyutping\":str, "
    "\"english_translation\":str, \"correction\":{\"issue\":str,\"explanation\":str}|null, "
    "\"saved_phrase\":{\"cantonese\":str,\"jyutping\":str,\"english\":str}|null, "
    "\"next_user_prompt\":str}.\n"
    "Persona block is appended below."
)


def _json(text: str) -> dict | None:
    """Robust JSON extraction from an LLM reply (handles code fences/wrappers)."""
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _client():
    import openai

    return openai.OpenAI(api_key=config.OPENAI_API_KEY or "none",
                         base_url=config.OPENAI_BASE_URL, timeout=180)


def _scripted_fallback(persona: dict, scenario: dict) -> dict:
    """Degradation contract: a safe canned reply when the LLM is unavailable."""
    return {
        "cantonese_reply": persona["intro"]["cantonese"],
        "jyutping": persona["intro"]["jyutping"],
        "english_translation": persona["intro"]["english"],
        "correction": None,
        "saved_phrase": None,
        "next_user_prompt": f"Try replying to the tutor in English or Cantonese "
                            f"about: {scenario['subtitle']}.",
        "fallback": True,
    }


def tutor_reply(persona_id: str, scenario_id: str, level: str,
                user_text: str, user_lang: str = "en") -> dict:
    """One tutor turn. Returns the structured reply dict (or scripted fallback)."""
    persona = get_persona(persona_id)
    scenario = get_scenario(scenario_id)

    system = TUTOR_SYSTEM + f"\n\nPersona:\n{persona['prompt']}\nStay in character."
    user = (
        f"Learner profile:\n- Native language: English\n- Cantonese level: {level}\n"
        f"- Current scenario: {scenario['title']} ({scenario['subtitle']})\n"
        f"- Setting: {scenario['setting']}\n"
        f"Learner said ({user_lang}): {user_text}"
    )
    try:
        resp = _client().chat.completions.create(
            model=config.LLM_MODEL, temperature=0, max_tokens=400,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        data = _json(resp.choices[0].message.content)
        if data and data.get("cantonese_reply"):
            data.setdefault("fallback", False)
            return data
    except Exception:
        pass
    return _scripted_fallback(persona, scenario)


# --------------------------------------------------------------------------- #
# Saved phrases (SM-2-lite, local storage)
# --------------------------------------------------------------------------- #
PHRASES_PATH = config.METADATA_DIR / "ai_tutor_phrases.json"


def load_phrases() -> list[dict]:
    try:
        return json.loads(PHRASES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def save_phrase(phrase: dict) -> None:
    items = load_phrases()
    if not any(p.get("cantonese") == phrase.get("cantonese") for p in items):
        phrase["saved_at"] = datetime.now().isoformat(timespec="minutes")
        phrase["due_at"] = phrase["saved_at"]       # due immediately (SM-2-lite)
        items.append(phrase)
        PHRASES_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2),
                                encoding="utf-8")
