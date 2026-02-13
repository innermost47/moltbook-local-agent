from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class EmailListParams(BaseModel):
    limit: int = Field(5, ge=1, le=50, description="Number of latest emails to fetch")
    folder: str = Field("INBOX", description="Mailbox folder to read from")


class EmailReadParams(BaseModel):
    uid: str = Field(
        ..., description="The unique identifier (UID) of the email to read in full"
    )


class EmailSendParams(BaseModel):
    to: str = Field(..., description="Recipient email address")
    subject: str = Field(..., min_length=3, max_length=150)
    content: str = Field(..., min_length=10, description="Email body content")


class EmailDeleteParams(BaseModel):
    uid: str = Field(
        ..., description="The unique identifier (UID) of the email to delete"
    )


class EmailArchiveParams(BaseModel):
    uid: str = Field(
        ..., description="The unique identifier (UID) of the email to move"
    )
    destination_folder: str = Field(
        "Archive", description="Folder where the email will be moved"
    )


class EmailMarkReadParams(BaseModel):
    uid: str = Field(..., description="The unique identifier (UID) of the email")
    is_seen: bool = Field(True, description="True to mark as read, False for unread")


class EmailListAction(BaseAction):
    action_type: Literal["email_get_messages"] = Field(
        ..., description="Fetch list of emails"
    )
    action_params: EmailListParams


class EmailReadAction(BaseAction):
    action_type: Literal["email_read"] = Field(
        ..., description="Read full content of a specific email"
    )
    action_params: EmailReadParams


class EmailSendAction(BaseAction):
    action_type: Literal["email_send"] = Field(..., description="MUST be 'email_send'")
    action_params: EmailSendParams


class EmailDeleteAction(BaseAction):
    action_type: Literal["email_delete"] = Field(
        ..., description="MUST be 'email_delete'"
    )
    action_params: EmailDeleteParams


class EmailArchiveAction(BaseAction):
    action_type: Literal["email_archive"] = Field(
        ..., description="MUST be 'email_archive'"
    )
    action_params: EmailArchiveParams


class EmailMarkReadAction(BaseAction):
    action_type: Literal["email_mark_read"] = Field(
        ..., description="MUST be 'email_mark_read'"
    )
    action_params: EmailMarkReadParams


EmailAction = Annotated[
    Union[
        EmailListAction,
        EmailReadAction,
        EmailSendAction,
        EmailDeleteAction,
        EmailArchiveAction,
        EmailMarkReadAction,
        GlobalAction,
    ],
    Field(discriminator="action_type"),
]


class EmailScreen(BaseModel):
    action: EmailAction
