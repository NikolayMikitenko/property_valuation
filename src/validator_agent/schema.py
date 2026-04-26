from pydantic import BaseModel
from typing import Literal

class PropertyValidationResult(BaseModel):
    decision: Literal["approved", "declined"]
    reason: str