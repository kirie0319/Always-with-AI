# html_routes/html_mobility.py
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/mobility", response_class=HTMLResponse)
async def mobility_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/mobility.html", {"request": request, "username": request.session.get("username")})

@router.get("/mobility/proposal", response_class=HTMLResponse)
async def proposal_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/proposal.html", {"request": request, "username": request.session.get("username")})

@router.get("/mobility/knowledge", response_class=HTMLResponse)
async def mobility_knowledge_page(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("mobility/knowledge.html", {"request": request, "username": request.session.get("username")})