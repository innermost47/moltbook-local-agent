from pydantic import BaseModel, Field
from typing import Literal, Union, Annotated
from src.screens.global_actions import GlobalAction
from src.screens.base import BaseAction


class EmailListParams(BaseModel):
    limit: int = Field(5, ge=1, le=50, description="Number of emails to fetch")
    folder: str = Field("INBOX", description="Mailbox folder")


class EmailReadParams(BaseModel):
    uid: str = Field(..., description="Email UID to read")


class EmailSendParams(BaseModel):
    to: str = Field(..., description="Recipient email")
    subject: str = Field(..., min_length=3, max_length=150)
    content: str = Field(..., min_length=10, description="Email body")
    reply_to_uid: str = Field(
        ...,
        description="UID of email being replied to (required - no new emails without reply)",
    )


class EmailDeleteParams(BaseModel):
    uid: str = Field(..., description="Email UID to delete")


class EmailArchiveParams(BaseModel):
    uid: str = Field(..., description="Email UID to move")
    destination_folder: str = Field("Archive", description="Destination folder")


class EmailMarkReadParams(BaseModel):
    uid: str = Field(..., description="Email UID")
    is_seen: bool = Field(True, description="True=read, False=unread")


class EmailListAction(BaseAction):
    action_type: Literal["email_get_messages"] = "email_get_messages"
    action_params: EmailListParams


class EmailReadAction(BaseAction):
    action_type: Literal["email_read"] = "email_read"
    action_params: EmailReadParams


class EmailSendAction(BaseAction):
    action_type: Literal["email_send"] = "email_send"
    action_params: EmailSendParams


class EmailDeleteAction(BaseAction):
    action_type: Literal["email_delete"] = "email_delete"
    action_params: EmailDeleteParams


class EmailArchiveAction(BaseAction):
    action_type: Literal["email_archive"] = "email_archive"
    action_params: EmailArchiveParams


class EmailMarkReadAction(BaseAction):
    action_type: Literal["email_mark_read"] = "email_mark_read"
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
