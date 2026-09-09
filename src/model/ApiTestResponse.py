from pydantic import BaseModel

class ApiTestResponseModel(BaseModel):
    method:str
    endpoint:str
    purpose:str
    test_cases:list[str]