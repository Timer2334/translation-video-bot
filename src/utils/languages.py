from enum import Enum


class InputLanguage(Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    CHINESE = "zh"
    KOREAN = "ko"
    ARABIC = "ar"
    FRENCH = "fr"
    ITALIAN = "it"
    SPANISH = "es"
    GERMAN = "de"
    JAPANESE = "ja"


class OutputLanguage(Enum):
    RUSSIAN = "ru"
    ENGLISH = "en"
    KAZAKH = "kk"


SOURCE_LANGS = {
    "ru": "русский",
    "en": "английский",
    "zh": "китайский",
    "ko": "корейский",
    "ar": "арабский",
    "fr": "французский",
    "it": "итальянский",
    "es": "испанский",
    "de": "немецкий",
    "ja": "японский",
}
TARGET_LANGS = {
    "ru": "русский",
    "en": "английский",
    "kk": "казахский"
}
