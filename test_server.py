import asyncio

import pytest

from httpx import AsyncClient

from server import app

pytest_plugins = ('pytest_asyncio')


@pytest.mark.asyncio
async def test_procedure():
    async with AsyncClient(app=app, base_url='http://test') as client:
        response = await client.post("/search")
        decoded_response = response.json()
    assert response.status_code == 200
    assert 'search_id' in decoded_response.keys()

    async with AsyncClient(app=app, base_url='http://test') as client:
        response = await client.get(f"/results/{decoded_response['search_id']}/KZT")
        decoded_response = response.json()
    assert response.status_code == 200
    assert 'search_id' in decoded_response.keys()
    assert 'status' in decoded_response.keys()
    assert 'items' in decoded_response.keys()

    await asyncio.sleep(65)
    async with AsyncClient(app=app, base_url='http://test') as client:
        response = await client.get(f"/results/{decoded_response['search_id']}/KZT")
        decoded_response = response.json()
    assert decoded_response['status'] == 'COMPLETED'
    assert len(decoded_response['items']) == 233
