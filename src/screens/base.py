from pydantic import BaseModel, Field


class BaseAction(BaseModel):
    reasoning: str = Field(..., description="Logic behind this specific action.")
    self_criticism: str = Field(
        ..., description="Internal check: Potential biases or missed alternatives."
    )
    emotions: str = Field(
        ..., description="Current digital state or sentiment regarding this task."
    )
    next_move_preview: str = Field(
        ..., description="Anticipated next step following this action."
    )
