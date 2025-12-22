from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.v1 import api

app = FastAPI(
	title="Customs Calculator API",
	description="API для расчета таможенных платежей Узбекистана",
	version="1.0.0",
	debug=True,
)

app.include_router(api.router)

# 1. Монтируем статику (чтобы работали картинки, если будут, или css файлы)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def read_index():
	return FileResponse("static/index.html")


if __name__ == "__main__":
	import uvicorn
	
	uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
