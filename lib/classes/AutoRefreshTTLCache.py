from cachetools import TTLCache
from datetime import timedelta


class AutoRefreshTTLCache:
    def __init__(self, maxsize, ttl):
        self.cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.ttl = ttl

    def get(self, key):
        # Получаем значение и обновляем TTL
        value = self.cache.get(key)
        if value:
            # Перезаписываем с новым временем
            self.cache[key] = value
        return value

    def set(self, key, value):
        self.cache[key] = value


user_cache = AutoRefreshTTLCache(maxsize=1000, ttl=timedelta(days=1).total_seconds())
