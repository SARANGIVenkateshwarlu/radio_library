"""LangChain LLM factory with an offline mock fallback.

If OPENAI_API_KEY is set, returns a ChatOpenAI (OpenAI-compatible) model
wrapped in LangChain chains. Otherwise returns MockLLM, which produces
deterministic placeholder output so the LangGraph pipeline is fully testable
without network access.
"""
from __future__ import annotations

import sys

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.prompts import ChatPromptTemplate

from . import config


class MockLLM(BaseChatModel):
    """Deterministic stand-in for a real chat model."""

    @property
    def _llm_type(self) -> str:
        return "mock-llm"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs) -> ChatResult:
        text = messages[-1].content if messages else ""
        body = text.split("：", 1)[-1].strip() or text
        if "vocabulary" in text.lower():
            out = _mock_vocab(body)
        elif "english" in text.lower():
            out = _mock_translate(body)
        else:
            out = body  # "corrected" = passthrough
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=out))])


_warned_mock = False


def get_llm() -> BaseChatModel:
    global _warned_mock
    if config.LLM_ENABLED:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.LLM_MODEL,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            temperature=0,
        )
    if not _warned_mock:
        print(
            "WARNING: no LLM API key configured — using offline mock translations "
            "(not real English). Add OPENAI_API_KEY (xai-...) to .env or "
            ".streamlit/secrets.toml. See README.",
            file=sys.stderr,
        )
        _warned_mock = True
    return MockLLM()


# LangChain chains (prompt | llm) used by the graph nodes.
CORRECT_PROMPT = ChatPromptTemplate.from_template(
    "你係一個廣東話編輯。修正以下電台語音轉寫嘅錯字同標點，"
    "保留口語風格，唔好改寫意思。如不確定，用〔?〕標記。"
    "只輸出修正後嘅句子本身，唔好加任何標題、解釋、前言或引號。\n\n原文：{text}"
)

TRANSLATE_PROMPT = ChatPromptTemplate.from_template(
    "Translate the following colloquial Cantonese radio sentence into natural, "
    "idiomatic English. Convey the MEANING (not a word-for-word gloss). Keep "
    "proper names and numbers exact. Output only the English translation, with "
    "no notes or romanisation.\n\nCantonese：{text}"
)

VOCAB_PROMPT = ChatPromptTemplate.from_template(
    "From the Cantonese sentence below, extract up to 3 useful vocabulary items for a learner. "
    "Output one per line, exactly in this format: word | jyutping | english meaning. "
    "No other text.\n\n句子：{text}"
)

GROUP_PROMPT = ChatPromptTemplate.from_template(
    "下面係一段電台節目嘅廣東話句子，每句前面有編號。請將佢哋分成若干段落，"
    "每段 3 至 6 句，喺轉換話題或者有明顯停頓嘅位置分段。"
    "只輸出一行，列出每段第一句嘅編號，用逗號分隔（例如：1,5,10）。唔好有其他文字。"
    "\n\n{text}"
)

REVIEW_PROMPT = ChatPromptTemplate.from_template(
    "你係一個嚴謹嘅廣東話學習材料審稿人。下面係一段電台節目嘅逐句轉寫，"
    "每行格式：編號. CANT: <廣東話> | JYUT: <粵拼> | ENG: <英文>。\n"
    "請檢查：(a) 廣東話轉寫有冇錯字；(b) 粵拼拼音準唔準；(c) 英文翻譯準唔準確、地唔地道；"
    "(d) 有冇明顯漏譯。只做評估，唔好改寫內容。\n"
    "只輸出一個 JSON 物件（唔好有其他文字、唔好用 code fence），格式如下：\n"
    '{{"accuracy_score": <0-100 嘅整數>, "summary": "<一句總結>", '
    '"issues": [{{"segment": <編號>, "problem": "<問題>", "suggestion": "<建議>"}}], '
    '"flagged_segments": [<有問題嘅編號>]}}\n\n轉寫內容：\n{text}'
)

# Curated sentence-level translations for known transcripts (real English,
# offline). Unknown sentences fall back to word-by-word glossing via lexicon.
_SENTENCE_TRANSLATIONS = {
    # demo news transcript
    "各位聽眾早晨，歡迎收聽今日嘅新聞報道。":
        "Good morning, listeners — welcome to today's news report.",
    "今日天氣比較潮濕，下午可能會有驟雨。":
        "The weather is relatively humid today, and there may be showers in the afternoon.",
    "天文台提醒市民出門口之前記得帶遮。":
        "The Hong Kong Observatory reminds everyone to bring an umbrella before heading out.",
    "交通方面，港鐵荃灣綫而家服務正常。":
        "As for traffic, the MTR Tsuen Wan Line is currently operating normally.",
    "不過紅磡海底隧道往香港方向交通擠塞，車龍排到去理工大學。":
        "However, traffic through the Cross-Harbour Tunnel towards Hong Kong Island is "
        "congested, with the queue stretching back to the Polytechnic University.",
    # real RTHK5 戲曲之夜 recording (ASR output, some names approximate)
    "12.09分,發射西洋記旁邊的你繼續收聽香港電台第五台的戲曲之夜":
        "12:09 — you are continuing to listen to Chinese Opera Night on RTHK Radio 5.",
    "即國際入面繼續有黃海為大家注持著節目":
        "In the programme, our host Wong Hoi continues to present the show for everyone.",
    "來到今個小時的節目時間,我們會繼續收聽中州湖諜夢的故事":
        "Coming up in this hour, we will continue listening to the story of "
        "「中州湖諜夢」 (opera excerpt, title as transcribed).",
    "我們剛剛在新聞簡報之前,分別收聽過三場內容":
        "Just before the news bulletin, we listened to three separate excerpts.",
    "包括煮鮮粉、辣汁和蒸蟲這三個部分":
        "They included the three excerpts 「煮鮮粉」, 「辣汁」 and 「蒸蟲」 "
        "(titles as transcribed by ASR).",
    "而今個小時會收聽到的會包括煮烤電、試妻還有協官這三場戲":
        "And this hour we will hear three opera excerpts: 「煮烤電」, 「試妻」 and "
        "「協官」 (titles as transcribed by ASR).",
    "不過在開始收聽之前,也要看大家現時的室外":
        "But before we start listening, let's look at the current outdoor conditions.",
}

# Lexicon: word -> (jyutping, english). Used for vocabulary extraction and
# word-by-word fallback translation when no real LLM is configured.
LEXICON = {
    # demo news
    "聽眾": ("ting1 zung3", "listeners / audience"),
    "早晨": ("zou2 san4", "good morning"),
    "歡迎": ("fun1 jing4", "welcome"),
    "收聽": ("sau1 ting3", "listen to (radio)"),
    "今日": ("gam1 jat6", "today"),
    "新聞": ("san1 man4", "news"),
    "報道": ("bou3 dou6", "report"),
    "天氣": ("tin1 hei3", "weather"),
    "比較": ("bei2 gaau3", "relatively / comparatively"),
    "潮濕": ("ciu4 sap1", "humid"),
    "下午": ("haa6 ng5", "afternoon"),
    "可能": ("ho2 nang4", "maybe / possibly"),
    "驟雨": ("zau6 jyu5", "sudden shower"),
    "天文台": ("tin1 man4 toi4", "Hong Kong Observatory"),
    "提醒": ("tai4 sing2", "remind"),
    "市民": ("si5 man4", "citizens / the public"),
    "出門口": ("ceot1 mun4 hau2", "go out / leave home"),
    "之前": ("zi1 cin4", "before"),
    "記得": ("gei3 dak1", "remember to"),
    "帶遮": ("daai3 ze1", "bring an umbrella"),
    "交通": ("gaau1 tung1", "traffic / transport"),
    "方面": ("fong1 min6", "aspect / regarding"),
    "港鐵": ("gong2 tit3", "MTR"),
    "荃灣綫": ("cyun4 waan1 sin3", "Tsuen Wan Line"),
    "而家": ("ji4 gaa1", "now / at present"),
    "服務": ("fuk6 mou6", "service"),
    "正常": ("zing3 soeng4", "normal"),
    "不過": ("bat1 gwo3", "however / but"),
    "紅磡": ("hung4 ham3", "Hung Hom"),
    "海底隧道": ("hoi2 dai2 seoi6 dou6", "Cross-Harbour Tunnel"),
    "香港": ("hoeng1 gong2", "Hong Kong"),
    "方向": ("fong1 hoeng3", "direction"),
    "擠塞": ("zai1 sak1", "congested / jammed"),
    "車龍": ("ce1 lung4", "traffic queue"),
    "排到": ("paai4 dou3", "queue stretching to"),
    "理工大學": ("lei5 gung1 daai6 hok6", "Polytechnic University"),
    # RTHK5 opera programme
    "香港電台": ("hoeng1 gong2 din6 toi4", "RTHK (Radio Television Hong Kong)"),
    "第五台": ("dai6 ng5 toi4", "Radio 5"),
    "戲曲之夜": ("hei3 kuk1 zi1 je6", "Chinese Opera Night (programme name)"),
    "戲曲": ("hei3 kuk1", "Chinese opera"),
    "繼續": ("gai3 zuk6", "continue"),
    "節目": ("zit3 muk6", "programme / show"),
    "主持": ("zyu2 ci4", "to host / presenter"),
    "大家": ("daai6 gaa1", "everyone"),
    "今個": ("gam1 go3", "this (current)"),
    "小時": ("siu2 si4", "hour"),
    "時間": ("si4 gaan3", "time"),
    "我們": ("ngo5 mun4", "we / us"),
    "故事": ("gu3 si6", "story"),
    "剛剛": ("gong1 gong1", "just now"),
    "新聞簡報": ("san1 man4 gaan2 bou3", "news bulletin"),
    "分別": ("fan1 bit6", "respectively / separately"),
    "三場": ("saam1 coeng4", "three excerpts/acts"),
    "內容": ("noi6 jung4", "content"),
    "包括": ("baau1 kut3", "including"),
    "部分": ("bou6 fan6", "part / section"),
    "開始": ("hoi1 ci2", "begin / start"),
    "現時": ("jin6 si4", "currently / at present"),
    "室外": ("sat1 ngoi6", "outdoors / outdoor"),
    "還有": ("waan4 jau5", "and also / in addition"),
    "來到": ("loi4 dou3", "coming to / arriving at"),
}


def _mock_translate(sentence: str) -> str:
    if sentence in _SENTENCE_TRANSLATIONS:
        return _SENTENCE_TRANSLATIONS[sentence]
    # fallback: word-by-word gloss, longest match first
    out, rest = [], sentence
    words = sorted(LEXICON, key=len, reverse=True)
    while rest:
        hit = next((w for w in words if rest.startswith(w)), None)
        if hit:
            out.append(LEXICON[hit][1])
            rest = rest[len(hit):]
        else:
            rest = rest[1:]
    if out:
        return "[rough gloss] " + " ".join(out)
    # Never echo the Cantonese source as if it were English — that makes the
    # PDF look like the translation is missing. Mark it explicitly instead.
    return "[no translation — configure an LLM for real English]"


def _mock_vocab(source_text: str) -> str:
    hits = [w for w in sorted(LEXICON, key=len, reverse=True) if w in source_text]
    seen, lines = set(), []
    for w in hits:
        if any(w in s for s in seen):  # skip substrings of already-listed words
            continue
        seen.add(w)
        jyut, eng = LEXICON[w]
        lines.append(f"{w} | {jyut} | {eng}")
        if len(lines) >= 4:
            break
    return "\n".join(lines) or "（無）"


def correct_chain(llm: BaseChatModel | None = None):
    return CORRECT_PROMPT | (llm or get_llm())


def translate_chain(llm: BaseChatModel | None = None):
    return TRANSLATE_PROMPT | (llm or get_llm())


def vocab_chain(llm: BaseChatModel | None = None):
    return VOCAB_PROMPT | (llm or get_llm())


def group_chain(llm: BaseChatModel | None = None):
    return GROUP_PROMPT | (llm or get_llm())


def review_chain(llm: BaseChatModel | None = None):
    return REVIEW_PROMPT | (llm or get_llm())
