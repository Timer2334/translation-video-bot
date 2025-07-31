from config.settings import AUDIO_PATH, BASE_DIR, OUTPUT_PATH
from src.services.translator.merge_video_audio import merge_video_audio


def merge_video_audio_test():
    # node_js(
    #     id="N-UNVZ4Qg3c",
    #     audio_path=AUDIO_PATH,
    #     audio_name="xxx",
    #     input_lang="en",
    #     output_lang="ru"
    # )
    merge_video_audio(
        video_path= BASE_DIR / "data/temp/video.mkv",
        audio_path=f"{AUDIO_PATH}/xxx.mp3",
        merged_video_path=OUTPUT_PATH / "out.mp4"
    )

if __name__ == '__main__':
    merge_video_audio_test()
