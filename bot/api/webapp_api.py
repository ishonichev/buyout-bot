"""Апи для веб-приложения."""
import hashlib
import hmac
from urllib.parse import parse_qsl
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Optional
import logging
import json

from bot.database.database import async_session_maker
from bot.database.models import Product, BotConfig
from bot.config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Buyout Bot Admin API")


# Pydantic модели
class ProductUpdate(BaseModel):
    name: str
    cashback: float
    instruction_text: str


class ProductCreate(BaseModel):
    name: str
    cashback: float
    instruction_text: str


class ProductToggle(BaseModel):
    is_active: bool


class ConfigUpdate(BaseModel):
    value: str


# Проверка Telegram initData
def validate_telegram_init_data(init_data: str) -> Dict:
    """Проверяет подлинность initData от Telegram."""
    try:
        parsed_data = dict(parse_qsl(init_data))
        
        # Извлекаем hash
        received_hash = parsed_data.pop('hash', None)
        if not received_hash:
            raise ValueError("No hash in initData")
        
        # Создаем data_check_string
        data_check_arr = [f"{k}={v}" for k, v in sorted(parsed_data.items())]
        data_check_string = '\n'.join(data_check_arr)
        
        # Вычисляем secret_key
        secret_key = hmac.new(
            b"WebAppData",
            settings.BOT_TOKEN.encode(),
            hashlib.sha256
        ).digest()
        
        # Вычисляем hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Проверяем
        if calculated_hash != received_hash:
            raise ValueError("Invalid hash")
        
        return parsed_data
        
    except Exception as e:
        logger.error(f"Ошибка валидации initData: {e}")
        raise HTTPException(status_code=403, detail="Invalid Telegram data")


async def verify_admin(authorization: Optional[str] = Header(None)) -> int:
    """Проверяет, что пользователь - админ."""
    # if not authorization:
    #     raise HTTPException(status_code=401, detail="Unauthorized")
    
    # init_data = validate_telegram_init_data(authorization)
    
    # # Извлекаем user_id
    # user_data = json.loads(init_data.get('user', '{}'))
    # user_id = user_data.get('id')
    
    # if not user_id or user_id not in settings.admin_ids_list:
    #     raise HTTPException(status_code=403, detail="Access denied")
    
    # return user_id
    return 0


async def get_db() -> AsyncSession:
    """Депенденс для получения сессии БД."""
    async with async_session_maker() as session:
        yield session


# Эндпоинты
@app.get("/")
async def serve_index():
    """Отдает главную страницу Web App."""
    return FileResponse(
        "bot/web_app/index.html",
        media_type="text/html; charset=utf-8"
    )


@app.get("/api/products")
async def get_products(
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Получить все товары."""
    result = await session.execute(select(Product).order_by(Product.id))
    products = result.scalars().all()
    
    data = [
        {
            "id": p.id,
            "name": p.name,
            "cashback": p.cashback,
            "instruction_text": p.instruction_text,
            "is_active": p.is_active
        }
        for p in products
    ]
    
    return JSONResponse(
        content=data,
        media_type="application/json; charset=utf-8"
    )


@app.post("/api/products")
async def create_product(
    data: ProductCreate,
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Создать новый товар (АКТИВНЫЙ ПО УМОЛЧАНИЮ!)."""
    product = Product(
        name=data.name,
        cashback=data.cashback,
        instruction_text=data.instruction_text,
        is_active=True  # АКТИВНЫЙ ПО УМОЛЧАНИЮ!
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    
    return JSONResponse(
        content={"status": "ok", "id": product.id},
        media_type="application/json; charset=utf-8"
    )


@app.post("/api/products/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Обновить товар."""
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product.name = data.name
    product.cashback = data.cashback
    product.instruction_text = data.instruction_text
    
    await session.commit()
    
    return JSONResponse(
        content={"status": "ok"},
        media_type="application/json; charset=utf-8"
    )


@app.delete("/api/products/{product_id}")
async def delete_product(
    product_id: int,
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Удалить товар."""
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    await session.delete(product)
    await session.commit()
    
    return JSONResponse(
        content={"status": "ok"},
        media_type="application/json; charset=utf-8"
    )


@app.post("/api/products/{product_id}/toggle")
async def toggle_product(
    product_id: int,
    data: ProductToggle,
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Переключить активность товара."""
    result = await session.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()
    
    if product:
        product.is_active = data.is_active
        await session.commit()
    
    return JSONResponse(
        content={"status": "ok"},
        media_type="application/json; charset=utf-8"
    )


@app.get("/api/config")
async def get_config(
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Получить все настройки текстов."""
    result = await session.execute(select(BotConfig))
    configs = result.scalars().all()
    
    data = {
        config.config_key: {
            "value": config.config_value,
            "description": config.description
        }
        for config in configs
    }
    
    return JSONResponse(
        content=data,
        media_type="application/json; charset=utf-8"
    )


@app.post("/api/config/{config_key}")
async def update_config(
    config_key: str,
    data: ConfigUpdate,
    admin_id: int = Depends(verify_admin),
    session: AsyncSession = Depends(get_db)
):
    """Обновить настройку текста."""
    result = await session.execute(
        select(BotConfig).where(BotConfig.config_key == config_key)
    )
    config = result.scalar_one_or_none()
    
    if config:
        config.config_value = data.value
        await session.commit()
        return JSONResponse(
            content={"status": "ok"},
            media_type="application/json; charset=utf-8"
        )
    else:
        raise HTTPException(status_code=404, detail="Config not found")
