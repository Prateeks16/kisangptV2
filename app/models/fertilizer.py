from typing import Optional
from sqlmodel import SQLModel, Field

class FertilizerBase(SQLModel):
    crop_name: str = Field(index=True, unique=True)
    n_value: int
    p_value: int
    k_value: int

class Fertilizer(FertilizerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class FertilizerCreate(FertilizerBase):
    pass