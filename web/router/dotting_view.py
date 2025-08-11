from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from pathlib import Path

# 创建路由器
dotting_router = APIRouter(prefix="/view", tags=["dotting"])

# 创建模板对象，指定模板文件夹路径
templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


@dotting_router.get("/dot", name="dotting", response_class=HTMLResponse)
async def dotting(request: Request):
    # 渲染模板并传递上下文数据
    return templates.TemplateResponse(
        "labelimg_for_history_photos.html",
        {"request": request},
    )
