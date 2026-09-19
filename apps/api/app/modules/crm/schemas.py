from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
LeadStatus=Literal["new","contacted","interested","registration_started","converted","not_interested"]
class LeadCreate(BaseModel):
 model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
 name:str=Field(min_length=1,max_length=120); email:str=Field(default="",max_length=320); phone:str=Field(default="",max_length=32); source:str=Field(default="manual",max_length=80); campaign:str=Field(default="",max_length=120); notes:str=Field(default="",max_length=5000)
class LeadEdit(BaseModel):
 model_config=ConfigDict(extra="forbid",str_strip_whitespace=True)
 status:LeadStatus; assigned_user_id:UUID|None=None; notes:str=Field(default="",max_length=5000); expected_version:int=Field(ge=1)
class LeadView(BaseModel):
 id:UUID; name:str; email:str; phone:str; source:str; campaign:str; status:LeadStatus; assigned_user_id:UUID|None; notes:str; version:int
class LeadList(BaseModel):
 items:list[LeadView]; next_cursor:UUID|None
