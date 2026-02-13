import smtplib
from email.message import EmailMessage
from typing import Dict, Any
from imap_tools import MailBox, MailMessageFlags
from bs4 import BeautifulSoup
from src.utils import log
from src.utils.exceptions import (
    SystemLogicError,
    APICommunicationError,
    FormattingError,
    ResourceNotFoundError,
    AccessDeniedError,
)


class EmailHandler:
    def __init__(self, host, smtp_host, user, password, test_mode=False):
        self.host = host
        self.smtp_host = smtp_host
        self.user = user
        self.password = password
        self.test_mode = test_mode
        self.mailbox = MailBox(self.host)
        self._authenticate()

    def _authenticate(self):
        try:
            self.mailbox.login(self.user, self.password, initial_folder="INBOX")
            log.info(f"📥 Mailbox connected: {self.user}")
        except Exception as e:
            log.error(f"❌ Email authentication failed: {e}")
            raise AccessDeniedError(
                message=f"Could not authenticate to mail server: {str(e)}",
                suggestion="Check your email credentials (IMAP_SERVER, EMAIL, PASSWORD) in settings.",
            )

    def handle_get_messages(self, params: Any) -> Dict:

        limit = getattr(params, "limit", 5)

        if limit < 1 or limit > 50:
            raise FormattingError(
                message=f"Invalid limit value: {limit}. Must be between 1-50.",
                suggestion="Set 'limit' parameter between 1 and 50.",
            )

        messages = []

        try:
            for msg in self.mailbox.fetch(limit=limit, reverse=True):
                body = msg.text or ""

                if not body.strip() and msg.html:
                    body = self._clean_html(msg.html)

                messages.append(
                    {
                        "uid": msg.uid,
                        "subject": msg.subject,
                        "from": msg.from_,
                        "date": msg.date.isoformat() if msg.date else None,
                        "body": body[:2000],
                    }
                )

            if not messages:
                return {"success": True, "data": "Inbox is empty."}

            return {"success": True, "data": messages}

        except TimeoutError:
            raise APICommunicationError(
                message="IMAP server connection timed out.",
                suggestion="Try again. Mail server may be slow or down.",
                api_name="IMAP Server",
            )
        except ConnectionError:
            raise APICommunicationError(
                message="Lost connection to IMAP server.",
                suggestion="Check network connection or try again later.",
                api_name="IMAP Server",
            )
        except Exception as e:
            log.error(f"❌ Failed to fetch emails: {e}")
            raise SystemLogicError(f"Email fetch failed: {str(e)}")

    def _clean_html(self, html_content: str) -> str:
        try:
            soup = BeautifulSoup(html_content, "lxml")

            for tag in ["script", "style", "head", "title", "meta"]:
                for element in soup(tag):
                    element.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return "\n".join(
                [line.strip() for line in text.splitlines() if line.strip()]
            )
        except Exception as e:
            log.warning(f"⚠️ HTML cleaning failed: {e}")
            return "[HTML content - parsing failed]"

    def handle_email_send(self, params: Any) -> Dict:

        if not hasattr(params, "to") or not params.to:
            raise FormattingError(
                message="Missing 'to' parameter.",
                suggestion="Provide recipient email address in 'to' field.",
            )

        if not hasattr(params, "content") or not params.content:
            raise FormattingError(
                message="Missing 'content' parameter.",
                suggestion="Provide email body content in 'content' field.",
            )

        recipient = params.to
        subject = getattr(params, "subject", "Automated Update")
        content = params.content

        if "@" not in recipient or "." not in recipient.split("@")[-1]:
            raise FormattingError(
                message=f"Invalid email format: {recipient}",
                suggestion="Provide a valid email address (e.g., user@example.com).",
            )

        if len(content.strip()) < 10:
            raise FormattingError(
                message="Email content is too short (< 10 characters).",
                suggestion="Provide meaningful email content (at least 10 characters).",
            )

        try:
            msg = EmailMessage()
            msg.set_content(content)
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = recipient

            with smtplib.SMTP(self.smtp_host, 587) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            log.success(f"📤 Email dispatched to {recipient}")
            return {"success": True, "data": f"Message sent to {recipient}."}

        except smtplib.SMTPAuthenticationError:
            raise AccessDeniedError(
                message="SMTP authentication failed.",
                suggestion="Check your email credentials (SMTP_HOST, EMAIL, PASSWORD).",
            )
        except smtplib.SMTPRecipientsRefused:
            raise FormattingError(
                message=f"Recipient '{recipient}' rejected by server.",
                suggestion="Check the recipient email address is valid and accepts mail.",
            )
        except smtplib.SMTPServerDisconnected:
            raise APICommunicationError(
                message="SMTP server disconnected unexpectedly.",
                suggestion="Try again. Mail server may be unstable.",
                api_name="SMTP Server",
            )
        except TimeoutError:
            raise APICommunicationError(
                message="SMTP connection timed out.",
                suggestion="Try again. Mail server may be slow or down.",
                api_name="SMTP Server",
            )
        except Exception as e:
            log.error(f"❌ SMTP Failure: {e}")
            raise SystemLogicError(f"Email send failed: {str(e)}")

    def handle_send_email_html(self, params: Any) -> Dict:

        if not hasattr(params, "to") or not params.to:
            raise FormattingError(
                message="Missing 'to' parameter.",
                suggestion="Provide recipient email address in 'to' field.",
            )

        if not hasattr(params, "content") or not params.content:
            raise FormattingError(
                message="Missing 'content' parameter.",
                suggestion="Provide email HTML content in 'content' field.",
            )

        recipient = params.to
        subject = getattr(params, "subject", "Automated Update")
        html_content = params.content

        if "@" not in recipient or "." not in recipient.split("@")[-1]:
            raise FormattingError(
                message=f"Invalid email format: {recipient}",
                suggestion="Provide a valid email address (e.g., user@example.com).",
            )

        if len(html_content.strip()) < 10:
            raise FormattingError(
                message="Email content is too short (< 10 characters).",
                suggestion="Provide meaningful email content (at least 10 characters).",
            )

        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = self.user
            msg["To"] = recipient

            msg.set_content(
                "This email contains HTML content. Please view in an HTML-compatible client."
            )

            msg.add_alternative(html_content, subtype="html")

            with smtplib.SMTP(self.smtp_host, 587) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)

            log.success(f"📤 HTML email dispatched to {recipient}")
            return {"success": True, "data": f"HTML message sent to {recipient}."}

        except smtplib.SMTPAuthenticationError:
            raise AccessDeniedError(
                message="SMTP authentication failed.",
                suggestion="Check your email credentials (SMTP_HOST, EMAIL, PASSWORD).",
            )
        except smtplib.SMTPRecipientsRefused:
            raise FormattingError(
                message=f"Recipient '{recipient}' rejected by server.",
                suggestion="Check the recipient email address is valid and accepts mail.",
            )
        except smtplib.SMTPServerDisconnected:
            raise APICommunicationError(
                message="SMTP server disconnected unexpectedly.",
                suggestion="Try again. Mail server may be unstable.",
                api_name="SMTP Server",
            )
        except TimeoutError:
            raise APICommunicationError(
                message="SMTP connection timed out.",
                suggestion="Try again. Mail server may be slow or down.",
                api_name="SMTP Server",
            )
        except Exception as e:
            log.error(f"❌ SMTP Failure: {e}")
            raise SystemLogicError(f"Email send failed: {str(e)}")

    def handle_mark_as_read(self, params: Any) -> Dict:

        if not hasattr(params, "uid") or not params.uid:
            raise FormattingError(
                message="Missing 'uid' parameter.",
                suggestion="Provide the email UID to mark as read.",
            )

        uid = params.uid

        try:
            self.mailbox.flag(uid, MailMessageFlags.SEEN, True)
            log.info(f"📖 Email {uid} marked as read.")
            return {"success": True, "data": f"Email {uid} marked as read."}

        except Exception as e:
            if "not found" in str(e).lower() or "invalid" in str(e).lower():
                raise ResourceNotFoundError(
                    message=f"Email UID '{uid}' not found in mailbox.",
                    suggestion="Call 'get_messages' to get valid UIDs.",
                )
            else:
                raise SystemLogicError(f"Failed to mark email as read: {str(e)}")

    def handle_archive_email(self, params: Any) -> Dict:

        if not hasattr(params, "uid") or not params.uid:
            raise FormattingError(
                message="Missing 'uid' parameter.",
                suggestion="Provide the email UID to archive.",
            )

        uid = params.uid
        folder = getattr(params, "destination", "Archive")

        if not folder or not folder.strip():
            raise FormattingError(
                message="Destination folder name is empty.",
                suggestion="Provide a valid folder name (e.g., 'Archive', 'Work', 'Personal').",
            )

        try:
            self.mailbox.move(uid, folder)
            log.info(f"📁 Email {uid} moved to {folder}")
            return {"success": True, "data": f"Email {uid} moved to {folder}."}

        except Exception as e:
            error_str = str(e).lower()
            if (
                "not found" in error_str
                or "invalid" in error_str
                or "no such" in error_str
            ):
                raise ResourceNotFoundError(
                    message=f"Email UID '{uid}' or folder '{folder}' not found.",
                    suggestion="Call 'get_messages' to get valid UIDs. Check folder name exists.",
                )
            elif "permission" in error_str or "access" in error_str:
                raise AccessDeniedError(
                    message=f"Cannot move email to folder '{folder}'. Permission denied.",
                    suggestion="Check folder permissions or use a different destination.",
                )
            else:
                raise SystemLogicError(f"Archiving failed: {str(e)}")

    def handle_delete_email(self, params: Any) -> Dict:

        if not hasattr(params, "uid") or not params.uid:
            raise FormattingError(
                message="Missing 'uid' parameter.",
                suggestion="Provide the email UID to delete.",
            )

        uid = params.uid

        try:
            self.mailbox.move(uid, "Trash")
            log.info(f"🗑️ Email {uid} moved to Trash")
            return {"success": True, "data": f"Email {uid} deleted (moved to Trash)."}

        except Exception as e:
            if "not found" in str(e).lower():
                raise ResourceNotFoundError(
                    message=f"Email UID '{uid}' not found.",
                    suggestion="Call 'get_messages' to get valid UIDs.",
                )
            else:
                raise SystemLogicError(f"Delete failed: {str(e)}")

    def handle_search_emails(self, params: Any) -> Dict:

        if not hasattr(params, "query") or not params.query:
            raise FormattingError(
                message="Missing 'query' parameter.",
                suggestion="Provide a search term to filter emails.",
            )

        query = params.query
        limit = getattr(params, "limit", 10)

        if limit < 1 or limit > 50:
            raise FormattingError(
                message=f"Invalid limit: {limit}. Must be between 1-50.",
                suggestion="Set limit between 1 and 50.",
            )

        try:
            results = []

            for msg in self.mailbox.fetch(limit=limit * 3, reverse=True):
                if (
                    query.lower() in msg.subject.lower()
                    or query.lower() in msg.from_.lower()
                ):

                    body = msg.text or ""
                    if not body.strip() and msg.html:
                        body = self._clean_html(msg.html)

                    results.append(
                        {
                            "uid": msg.uid,
                            "subject": msg.subject,
                            "from": msg.from_,
                            "date": msg.date.isoformat() if msg.date else None,
                            "body": body[:500],
                        }
                    )

                    if len(results) >= limit:
                        break

            if not results:
                return {"success": True, "data": f"No emails found matching '{query}'."}

            return {"success": True, "data": results}

        except Exception as e:
            raise SystemLogicError(f"Email search failed: {str(e)}")

    def close(self):
        try:
            self.mailbox.logout()
            log.info("🔌 Email session terminated.")
        except:
            pass
