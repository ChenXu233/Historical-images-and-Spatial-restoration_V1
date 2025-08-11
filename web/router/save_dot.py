from fastapi import APIRouter

from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/api", tags=["save_dot"])


@router.get("/save_dot")
async def save_dot(request):
    return Jinja2Templates(directory="web/templates").TemplateResponse(
        "save_dot.html", {"request": request}
    )
