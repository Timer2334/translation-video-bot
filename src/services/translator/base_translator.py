import abc

from src.utils.languages import InputLanguage, OutputLanguage


class BaseTranslator(abc.ABC):

    @abc.abstractmethod
    def run(
            self,
            video_path: str,
            audio_name: str,
            output_name: str,
            input_lang: InputLanguage,
            output_lang: OutputLanguage
    ): pass
