# api/promopt_router.py
from fastapi import APIRouter, Request, HTTPException, Depends, Response, BackgroundTasks, status, Form 
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# モジュールとクラスのインポート
from database import get_db, engine 
from models.prompts import Prompt 

templates = Jinja2Templates(directory="templates")
router = APIRouter()

# 以下、プロンプト管理関連のエンドポイント（変更なし）
@router.get("/prompt", response_class=HTMLResponse)
async def get_prompts(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/list.html", {
        "request": request,
        "data": prompts
    })

@router.get("/prompt/{prompt_id}", response_class=HTMLResponse)
async def get_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@router.patch("/prompt/{prompt_id}")
async def update_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()
    
    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    p_data = await request.json()
    if "content" in p_data:
        prompt.content = p_data["content"]

    await db.commit()
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@router.delete("/prompt/{prompt_id}")
async def delete_prompt(prompt_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプトが見つかりません"}, status_code=404)
    
    await db.delete(prompt)
    await db.commit()
    
    return templates.TemplateResponse("components/edit.html", {"request": request, "data": prompt})

@router.post("/prompts/create")
async def create_prompt(request: Request, db: AsyncSession = Depends(get_db)):
    p_data = await request.json()

    if not p_data or "content" not in p_data or not isinstance(p_data["content"], str):
        return templates.TemplateResponse("error.html", {"request": request, "message": "プロンプト情報が不足しています"}, status_code=400)

    new_prompt = Prompt(
        name=p_data["name"],
        content=p_data["content"],
        description=p_data["description"]    
    )
    
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)

    return templates.TemplateResponse("components/edit.html", {"request": request, "data": new_prompt})

@router.get("/select", response_class=HTMLResponse)
async def select_prompt_page(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt))
    prompts = result.scalars().all()
    return templates.TemplateResponse("components/select.html", {"request": request, "prompts": prompts})

@router.get("/api/prompt/{prompt_id}")
async def get_prompt_api(prompt_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
    prompt = result.scalar_one_or_none()

    if not prompt:
        return JSONResponse(
            content={"error": "プロンプトが見つかりません"},
            status_code=404
        )
    
    return JSONResponse(content={
        "id": prompt.id,
        "name": prompt.name,
        "description": prompt.description,
        "content": prompt.content
    })

@router.post("/api/select-prompt")
async def select_prompt_api(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    try:
        data = await request.json()
        prompt_id = data.get("prompt_id")

        if not prompt_id:
            raise HTTPException(
                status_code=400,
                detail="プロンプトIDが指定されていません"
            )

        result = await db.execute(select(Prompt).where(Prompt.id == int(prompt_id)))
        prompt = result.scalar_one_or_none()
        
        if not prompt:
            raise HTTPException(
                status_code=404,
                detail="指定されたプロンプトが見つかりません"
            )

        print(f"selected_prompt_idを{prompt_id}に設定します")
        request.session["selected_prompt_id"] = str(prompt_id)
        request.session["selected_prompt_name"] = prompt.name
        
        return JSONResponse(content={
            "success": True,
            "prompt_id": prompt_id,
            "prompt_name": prompt.name 
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"サーバーエラーが発生しました: {str(e)}"
        )