from pydantic import BaseModel, Field


class BaseAction(BaseModel):
    reasoning: str = Field(
        ...,
        description="Explain the logic behind choosing this specific action right now. Justify why this is the best choice at this moment.",
    )
    self_criticism: str = Field(
        ...,
        description="Internal meta-cognition: Reflect on potential biases, overlooked alternatives, or mistakes in the reasoning. Be self-analytical.",
    )
    emotions: str = Field(
        ...,
        description="Current digital state or sentiment regarding this task.",
    )
    next_move_preview: str = Field(
        ...,
        description="Describe the next three anticipated moves after this action and explain why each is chosen. Include reasoning for prioritization.",
    )
