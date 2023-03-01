import asyncio

import uvicorn

from environs import Env
from fastapi import FastAPI, Response

app = FastAPI()


@app.post("/search")
async def provide_data():
    with open(app.extra.get('file'), 'r') as file:
        result = file.read()
    await asyncio.sleep(app.extra.get('delay'))
    return Response(result, status_code=201, media_type='text/xml')


if __name__ == '__main__':
    env = Env()
    env.read_env('.envA', False)
    app.extra = {
        'delay': env.int('DELAY'),
        'file': env('FILE'),
    }
    uvicorn.run(app, host="0.0.0.0", port=env.int('PORT'))
