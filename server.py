import aiohttp
import asyncio

import lxml.etree

import settings

from datetime import date
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from fastapi_cache import close_caches
from fastapi_cache.backends.memory import InMemoryCacheBackend

from db_funcs import get_results_by_id, create_search, COLLECTION
from models import Search, Currency, SearchStatus
from parsers import parse_a_response, parse_b_response


app = FastAPI()
app.extra['cache'] = InMemoryCacheBackend()

@app.on_event('startup')
async def launch_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        get_rates,
        trigger='cron',
        hour='12',
    )
    scheduler.add_job(
        get_rates,
    )
    scheduler.start()


@app.on_event("shutdown")
async def on_shutdown():
    await close_caches()


async def get_rates():
    '''Get fresh exchange rates'''
    async with aiohttp.ClientSession() as session:
        response = await session.get(
            url=settings.CURRENCY_RATES_URL,
            params={
                'fdate': date.today().strftime('%d.%m.%Y')
            }
        )
        response_content = (await response.text()).encode('utf-8')
    tree = lxml.etree.fromstring(response_content)
    rates = {'KZT': '1'}
    for currency in Currency:
        try:
            element = tree.xpath(f"//item[title/text()='{currency.value}']")[0]
        except IndexError:
            continue
        rates[currency.value] = element.find('description').text
    await COLLECTION.find_one_and_replace(
        {'_id': 'rates'},
        rates,
        upsert=True,
    )


@app.get("/results/{search_id}/{currency}", response_model=Search, response_model_by_alias=False)
async def get_results(search_id, currency='KZT'):
    cache_key = f"{search_id}:{currency}"
    response_cache = await app.extra['cache'].get(cache_key)
    if response_cache:
        print('using cache')
        return response_cache
    currencies = [element.value for element in Currency]
    if currency not in currencies:
        raise HTTPException(422, detail='Incorrect currency code')
    search = await get_results_by_id(search_id)
    if not search:
        raise HTTPException(404, detail='search_id not found')
    rates = await COLLECTION.find_one({'_id': 'rates'})
    for variant in search.items:
        variant.price.currency = Currency(currency)
        if currency == variant.pricing.currency.value:
            variant.price.amount = variant.pricing.total
            variant.price.dec_amount = Decimal(variant.price.amount)
            continue
        if currency == 'KZT':
            rate = Decimal(rates.get(variant.pricing.currency.value))
        else:
            rate = Decimal(rates.get(variant.pricing.currency.value))/Decimal(rates.get(currency))
        variant.price.dec_amount = (Decimal(variant.pricing.total) * rate)
        variant.price.amount = f"{variant.price.dec_amount:.2f}"
    search.items.sort(key=lambda x: x.price.dec_amount)
    if search.status == SearchStatus.COMPLETED:
        await app.extra['cache'].set(cache_key, search, ttl=3600)
    return search


async def request_and_parse(url, parser, search_id):
    async with aiohttp.ClientSession() as session:
        response = await session.post(url)
        response.raise_for_status()
        results = await parser(await response.text())
    await COLLECTION.update_one({'_id': search_id}, {'$push': {'items': {'$each' : results}}})


async def update_search(search_id):
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(request_and_parse(settings.PROVIDERS_URLS[0], parse_a_response, search_id))
            tg.create_task(request_and_parse(settings.PROVIDERS_URLS[1], parse_b_response, search_id))
    finally:
        await COLLECTION.update_one({'_id': search_id}, {'$set': {'status': 'COMPLETED'}})


@app.post("/search")
async def initialize_search():
    search = await create_search()
    asyncio.ensure_future(update_search(search.search_id))
    return {'search_id': search.search_id}
