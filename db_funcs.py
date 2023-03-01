import uuid

import motor.motor_asyncio

import settings

from pydantic import parse_obj_as

from models import Search


COLLECTION = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_DB_URL).aviata.searches


async def get_results_by_id(id):
    awaiting_result = COLLECTION.find_one({'_id': id})
    result = await awaiting_result
    if not result:
        return None
    search = parse_obj_as(Search, result)
    return search


async def create_search():
    search = Search(search_id=uuid.uuid4().__str__())
    decoded = search.dict(by_alias=True)
    await COLLECTION.insert_one(decoded)
    return search
