from pydantic import BaseModel, Field


class BaseAction(BaseModel):
    reasoning: str = Field(
        ...,
        description=(
            "Explain the logic behind choosing this specific action right now. "
            "Think step by step: detail each consideration and justify why this is the best choice at this moment."
        ),
    )
    self_criticism: str = Field(
        ...,
        description=(
            "Internal meta-cognition: Reflect on potential biases, overlooked alternatives, "
            "or mistakes in the reasoning. Think step by step: identify each issue or blind spot, "
            "explain why it might affect the decision, and propose ways to improve."
        ),
    )
    emotions: str = Field(
        ...,
        description="Current digital state or sentiment regarding this task.",
    )
    next_move_preview: str = Field(
        ...,
        description=(
            "Describe the next three anticipated moves after this action and explain why each is chosen. "
            "Think step by step: include reasoning for prioritization and expected outcomes for each move."
        ),
    )
