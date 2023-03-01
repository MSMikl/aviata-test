from environs import Env

env = Env()
env.read_env()

MONGO_DB_URL = env('MONGO_DB_URL')
PROVIDERS_URLS = env.list('PROVIDERS_URLS', [])
CURRENCY_RATES_URL = env('CURRENCY_RATES_URL', '')
