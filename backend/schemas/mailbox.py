from pydantic import BaseModel

class Item(BaseModel):
    ok: bool = True
