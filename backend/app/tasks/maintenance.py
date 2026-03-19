from app.celery_app import celery
from app.core.config import settings

try:
    import redis
except ImportError:
    redis = None


@celery.task(name='app.tasks.maintenance.limpar_cache')
def limpar_cache():
    """Limpa chaves de cache expiradas do Redis."""
    if redis is None:
        return 'Redis client nao disponivel'
    try:
        r = redis.from_url(settings.REDIS_URL)
        keys = r.keys('mpcars2:cache:*')
        deleted = 0
        for key in keys:
            ttl = r.ttl(key)
            if ttl == -1:  # no expiry set
                r.expire(key, 3600)
            elif ttl == -2:  # already expired
                r.delete(key)
                deleted += 1
        return 'Cache limpo: {} chaves removidas de {} total'.format(deleted, len(keys))
    except Exception as e:
        return 'Erro ao limpar cache: {}'.format(str(e))
