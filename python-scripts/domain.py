from pydantic import BaseModel

class Message(BaseModel):
    msg: str

class DataModel(BaseModel):
    uuid: str
    msg: str
