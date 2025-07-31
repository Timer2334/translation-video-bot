from config.settings import TOKENS_PATH
from src.services.translator.fileTranslator.redis_youTube_limiter import RedisYouTubeLimiter

def redis_test():
    redis = RedisYouTubeLimiter(TOKENS_PATH)
    redis.increment_count()
    print(redis.get_count())

if __name__ == '__main__':
    redis_test()