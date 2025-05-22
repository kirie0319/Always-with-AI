# html_rotuers/html_main.py
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from models.prompts import Prompt
from sqlalchemy import select

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# メインアプリケーションエンドポイント
@router.get("/", response_class=HTMLResponse)
async def admin(request: Request, db: AsyncSession = Depends(get_db)):
    prompt_query = await db.execute(select(Prompt))
    available_prompts = prompt_query.scalars().all()
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin/admin.html", {"request": request, "available_prompts": available_prompts})
