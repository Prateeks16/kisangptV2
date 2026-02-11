import sys
import os
import asyncio
from sqlmodel import Session, create_engine, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add the root directory to path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.fertilizer import Fertilizer
from app.core.config import settings
from sqlmodel import SQLModel

# Copy your dictionary here
RAW_DATA = {
    "rice": {"N": 100, "P": 60, "K": 40},
    "wheat": {"N": 120, "P": 60, "K": 40},
    "maize": {"N": 150, "P": 75, "K": 50},
    "groundnut": {"N": 25, "P": 25, "K": 25},
    "cotton": {"N": 80, "P": 40, "K": 40},
    "sugarcane": {"N": 200, "P": 100, "K": 100},
    "potato": {"N": 120, "P": 80, "K": 100},
    "paddy": {"N": 100, "P": 60, "K": 40},
    "soybean": {"N": 30, "P": 60, "K": 30},
    "barley": {"N": 60, "P": 40, "K": 20},
    "sorghum": {"N": 90, "P": 45, "K": 45},
    "pearl_millet": {"N": 60, "P": 30, "K": 20},
    "finger_millet": {"N": 60, "P": 30, "K": 30},
    "oat": {"N": 80, "P": 40, "K": 20},
    "chickpea": {"N": 20, "P": 40, "K": 20},
    "pigeon_pea": {"N": 20, "P": 50, "K": 20},
    "black_gram": {"N": 20, "P": 40, "K": 20},
    "green_gram": {"N": 20, "P": 40, "K": 20},
    "lentil": {"N": 20, "P": 40, "K": 20},
    "pea": {"N": 20, "P": 40, "K": 20},
    "mustard": {"N": 80, "P": 40, "K": 40},
    "rapeseed": {"N": 80, "P": 40, "K": 40},
    "sunflower": {"N": 60, "P": 60, "K": 40},
    "sesame": {"N": 40, "P": 20, "K": 20},
    "linseed": {"N": 40, "P": 20, "K": 20},
    "castor": {"N": 60, "P": 40, "K": 40},
    "safflower": {"N": 40, "P": 20, "K": 20},
    "tobacco": {"N": 80, "P": 40, "K": 40},
    "jute": {"N": 80, "P": 40, "K": 40},
    "mesta": {"N": 60, "P": 30, "K": 30},
    "sugarbeet": {"N": 120, "P": 60, "K": 100},
    "carrot": {"N": 80, "P": 60, "K": 100},
    "onion": {"N": 100, "P": 50, "K": 50},
    "garlic": {"N": 100, "P": 50, "K": 50},
    "tomato": {"N": 120, "P": 60, "K": 60},
    "brinjal": {"N": 100, "P": 50, "K": 50},
    "chilli": {"N": 80, "P": 40, "K": 40},
    "capsicum": {"N": 80, "P": 40, "K": 40},
    "okra": {"N": 80, "P": 40, "K": 40},
    "cabbage": {"N": 120, "P": 60, "K": 60},
    "cauliflower": {"N": 120, "P": 60, "K": 60},
    "radish": {"N": 60, "P": 40, "K": 40},
    "turnip": {"N": 60, "P": 40, "K": 40},
    "spinach": {"N": 60, "P": 40, "K": 40},
    "fenugreek": {"N": 40, "P": 20, "K": 20},
    "coriander": {"N": 40, "P": 20, "K": 20},
    "cumin": {"N": 40, "P": 20, "K": 20},
    "fennel": {"N": 40, "P": 20, "K": 20},
    "dill": {"N": 40, "P": 20, "K": 20},
    "mint": {"N": 60, "P": 40, "K": 40},
    "basil": {"N": 40, "P": 20, "K": 20},
    "parsley": {"N": 40, "P": 20, "K": 20},
    "pumpkin": {"N": 60, "P": 40, "K": 40},
    "bottle_gourd": {"N": 60, "P": 40, "K": 40},
    "bitter_gourd": {"N": 60, "P": 40, "K": 40},
    "ridge_gourd": {"N": 60, "P": 40, "K": 40},
    "sponge_gourd": {"N": 60, "P": 40, "K": 40},
    "cucumber": {"N": 60, "P": 40, "K": 40},
    "watermelon": {"N": 60, "P": 40, "K": 40},
    "muskmelon": {"N": 60, "P": 40, "K": 40},
    "papaya": {"N": 100, "P": 60, "K": 60},
    "banana": {"N": 200, "P": 60, "K": 300},
    "mango": {"N": 100, "P": 50, "K": 100},
    "guava": {"N": 100, "P": 50, "K": 100},
    "sapota": {"N": 80, "P": 40, "K": 80},
    "pomegranate": {"N": 80, "P": 40, "K": 80},
    "citrus": {"N": 100, "P": 50, "K": 100},
    "grapes": {"N": 120, "P": 60, "K": 120},
    "apple": {"N": 80, "P": 40, "K": 80},
    "pear": {"N": 80, "P": 40, "K": 80},
    "peach": {"N": 80, "P": 40, "K": 80},
    "plum": {"N": 80, "P": 40, "K": 80},
    "apricot": {"N": 80, "P": 40, "K": 80},
    "cherry": {"N": 80, "P": 40, "K": 80},
    "strawberry": {"N": 80, "P": 40, "K": 80},
    "pineapple": {"N": 100, "P": 50, "K": 100},
    "jackfruit": {"N": 80, "P": 40, "K": 80},
    "cashew": {"N": 80, "P": 40, "K": 80},
    "coconut": {"N": 100, "P": 50, "K": 100},
    "arecanut": {"N": 100, "P": 50, "K": 100},
    "coffee": {"N": 80, "P": 40, "K": 80},
    "tea": {"N": 80, "P": 40, "K": 80},
    "rubber": {"N": 80, "P": 40, "K": 80},
    "oil_palm": {"N": 120, "P": 60, "K": 120},
    "betel_vine": {"N": 80, "P": 40, "K": 80},
    "turmeric": {"N": 80, "P": 40, "K": 80},
    "ginger": {"N": 80, "P": 40, "K": 80},
    "cardamom": {"N": 80, "P": 40, "K": 80},
    "black_pepper": {"N": 80, "P": 40, "K": 80},
    "clove": {"N": 80, "P": 40, "K": 80},
    "nutmeg": {"N": 80, "P": 40, "K": 80},
    "vanilla": {"N": 80, "P": 40, "K": 80},
    "areca": {"N": 80, "P": 40, "K": 80},
    "lemon_grass": {"N": 80, "P": 40, "K": 80},
    "sweet_potato": {"N": 80, "P": 40, "K": 80},
    "yam": {"N": 80, "P": 40, "K": 80},
    "colocasia": {"N": 80, "P": 40, "K": 80},
    "amaranthus": {"N": 60, "P": 40, "K": 40},
    "drumstick": {"N": 60, "P": 40, "K": 40},
    "beetroot": {"N": 80, "P": 40, "K": 80},
    "lettuce": {"N": 60, "P": 40, "K": 40},
    "broccoli": {"N": 80, "P": 40, "K": 80},
    "kale": {"N": 80, "P": 40, "K": 80},
    "leek": {"N": 60, "P": 40, "K": 40},
    "celery": {"N": 60, "P": 40, "K": 40},
    "artichoke": {"N": 80, "P": 40, "K": 80},
    "asparagus": {"N": 80, "P": 40, "K": 80}
}

async def init_db():
    engine = create_async_engine(settings.DATABASE_URL)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Insert Data
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for crop, values in RAW_DATA.items():
            # Check if exists
            result = await session.execute(select(Fertilizer).where(Fertilizer.crop_name == crop))
            existing = result.scalars().first()
            
            if not existing:
                print(f"Adding {crop}...")
                new_fert = Fertilizer(
                    crop_name=crop,
                    n_value=values['N'],
                    p_value=values['P'],
                    k_value=values['K']
                )
                session.add(new_fert)
        
        await session.commit()
        print("Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(init_db())