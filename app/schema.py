from datetime import datetime
from enum import Enum
from fastapi import Body
from pydantic import BaseModel
from typing import Union


class ItemType(str, Enum):
    FOLDER = "FOLDER"
    FILE = "FILE"


class Item(BaseModel):
    type: ItemType
    id: str
    parentId: Union[str, None] = None
    url: Union[str, None] = None
    size: Union[int, None] = None
    filename: Union[str, None] = None

    class Config:
        orm_mode = True


class Batch(BaseModel):
    items: list[Item] = Body(embed=True)
    updateDate: datetime

    class Config:
        orm_mode = True


'''
# method to parse several strings along with files
# async def imports(item: ItemForm = Depends(ItemForm.as_form), data: list[UploadFile] = File(...)):
# ...
class ItemForm(BaseModel):
    type: ItemType
    id: str
    parentId: Union[str, None]
    url: Union[str, None] = None
    size: Union[int, None] = None

    @classmethod
    def as_form(cls, type: ItemType = Form(...), id: str = Form(...),
                parentId: Union[str, None] = Form(...), url: Union[str, None] = Form(...),
                size: Union[int, None] = Form(...)) -> 'ItemForm':
        return cls(type=type, id=id, parentId=parentId, url=url, size=size)
'''
