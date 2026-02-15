from pydantic import BaseModel, Field


class BaseAction(BaseModel):
    reasoning: str = Field(..., description="Why now?")
    self_criticism: str = Field(..., description="Biases?")
    emotions: str = Field(..., description="Sentiment?")
    next_move_preview: str = Field(..., description="Next 3 moves?")
