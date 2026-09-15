from __future__ import annotations

import base64
import hashlib
import json
from email.message import EmailMessage
from email.policy import SMTP
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .adapter import (
    GMAIL_ARCHIVE_ACTION,
    GMAIL_DRAFT_ACTION,
    GMAIL_SEND_ACTION,
    GmailEffectError,
    GmailTransport,
)


GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"


class GoogleGmailTransportError(RuntimeError):
    """Google Gmail REST boundary failed closed without exposing credential material."""


def _b64url_decode(value: str) -> bytes:
    if not isinstance(value, str):
        raise GoogleGmailTransportError("Gmail payload body data is not text")
    padded = value + "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise GoogleGmailTransportError("Gmail payload body is not valid base64url") from exc


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _message_id_for_request(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:40]
    return f"<lac.{digest}@local-agent-controller.invalid>"


def _header_map(payload: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    headers = payload.get("headers", [])
    if not isinstance(headers, list):
        return result
    for item in headers:
        if not isinstance(item, Mapping):
            continue
        name = item.get("name")
        value = item.get("value")
        if isinstance(name, str) and isinstance(value, str):
            result[name.lower()] = value
    return result


def _plain_text_parts(payload: Mapping[str, Any]) -> list[str]:
    parts: list[str] = []
    mime_type = payload.get("mimeType")
    body = payload.get("body")
    if mime_type == "text/plain" and isinstance(body, Mapping):
        data = body.get("data")
        if isinstance(data, str) and data:
            try:
                parts.append(_b64url_decode(data).decode("utf-8", errors="replace"))
            except GoogleGmailTransportError:
                raise
    children = payload.get("parts")
    if isinstance(children, list):
        for child in children:
            if isinstance(child, Mapping):
                parts.extend(_plain_text_parts(child))
    return parts


def _normalize_message(raw: Mapping[str, Any]) -> dict[str, Any]:
    message_id = raw.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise GoogleGmailTransportError("Gmail message response lacks id")
    thread_id = raw.get("threadId")
    labels = raw.get("labelIds", [])
    snippet = raw.get("snippet", "")
    payload = raw.get("payload", {})
    if not isinstance(payload, Mapping):
        payload = {}
    headers = _header_map(payload)
    body_text = "\n".join(_plain_text_parts(payload))
    return {
        "id": message_id,
        "thread_id": thread_id if isinstance(thread_id, str) else None,
        "label_ids": [x for x in labels if isinstance(x, str)] if isinstance(labels, list) else [],
        "snippet": snippet if isinstance(snippet, str) else "",
        "from": headers.get("from"),
        "to": headers.get("to"),
        "cc": headers.get("cc"),
        "bcc": headers.get("bcc"),
        "subject": headers.get("subject"),
        "date": headers.get("date"),
        "message_id_header": headers.get("message-id"),
        "body": body_text,
    }


class GoogleGmailTransportFactory:
    """Builds a Gmail REST transport from an opaque OAuth access-token secret.

    Credential acquisition/refresh is intentionally delegated to SecretProvider.
    The factory accepts only an already-resolved bearer token and never persists it.
    """

    def __init__(
        self,
        *,
        opener: Callable[..., Any] | None = None,
        api_base: str = GMAIL_API_BASE,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not isinstance(api_base, str) or not api_base.startswith("https://"):
            raise GoogleGmailTransportError("api_base must be an https URL")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise GoogleGmailTransportError("timeout_seconds must be positive")
        self._opener = opener or urlopen
        self._api_base = api_base.rstrip("/")
        self._timeout = float(timeout_seconds)

    def create(self, *, account_resource: str, secret: object) -> GmailTransport:
        if not isinstance(account_resource, str) or not account_resource:
            raise GoogleGmailTransportError("account_resource must be non-empty")
        if not isinstance(secret, str) or not secret:
            raise GoogleGmailTransportError("Gmail bearer-token capability is unavailable")
        return GoogleGmailTransport(
            access_token=secret,
            opener=self._opener,
            api_base=self._api_base,
            timeout_seconds=self._timeout,
        )


class GoogleGmailTransport:
    __slots__ = ("_access_token", "_opener", "_api_base", "_timeout")

    def __init__(
        self,
        *,
        access_token: str,
        opener: Callable[..., Any],
        api_base: str,
        timeout_seconds: float,
    ) -> None:
        self._access_token = access_token
        self._opener = opener
        self._api_base = api_base
        self._timeout = timeout_seconds

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = self._api_base + path
        if query:
            url += "?" + urlencode(query, doseq=True)
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": "Bearer " + self._access_token,
                "Content-Type": "application/json",
            },
        )
        try:
            response = self._opener(req, timeout=self._timeout)
            raw = response.read()
        except HTTPError as exc:
            raise GoogleGmailTransportError(f"Gmail API returned HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise GoogleGmailTransportError("Gmail API request failed") from None
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleGmailTransportError("Gmail API returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise GoogleGmailTransportError("Gmail API response must be a JSON object")
        return parsed

    @staticmethod
    def _raw_message(message: Mapping[str, Any], *, request_id: str) -> str:
        attachment_hashes = message.get("attachment_hashes")
        if attachment_hashes:
            # B001 binds attachment hashes exactly, but the initial REST transport
            # accepts no attachment payload bytes. It therefore fails closed rather
            # than pretending hashed attachments were transmitted.
            raise GoogleGmailTransportError(
                "non-empty attachment_hashes require an attachment payload provider"
            )
        msg = EmailMessage()
        msg["To"] = ", ".join(message.get("to", []))
        cc = message.get("cc", [])
        bcc = message.get("bcc", [])
        if cc:
            msg["Cc"] = ", ".join(cc)
        if bcc:
            msg["Bcc"] = ", ".join(bcc)
        msg["Subject"] = str(message.get("subject", ""))
        msg["Message-ID"] = _message_id_for_request(request_id)
        msg["X-LAC-Request-ID"] = request_id
        msg.set_content(str(message.get("body", "")))
        return _b64url_encode(msg.as_bytes(policy=SMTP))

    def search(self, *, query: str, max_results: int) -> Mapping[str, Any]:
        raw = self._request_json(
            "GET",
            "/messages",
            query={"q": query, "maxResults": max_results},
        )
        messages = raw.get("messages", [])
        normalized = []
        if isinstance(messages, list):
            for item in messages:
                if not isinstance(item, Mapping):
                    continue
                message_id = item.get("id")
                thread_id = item.get("threadId")
                if isinstance(message_id, str) and message_id:
                    normalized.append(
                        {
                            "id": message_id,
                            "thread_id": thread_id if isinstance(thread_id, str) else None,
                        }
                    )
        token = raw.get("nextPageToken")
        return {
            "messages": normalized,
            "next_page_token": token if isinstance(token, str) else None,
            "result_size_estimate": raw.get("resultSizeEstimate") if isinstance(raw.get("resultSizeEstimate"), int) else None,
        }

    def read(self, *, message_id: str) -> Mapping[str, Any]:
        raw = self._request_json(
            "GET",
            "/messages/" + quote(message_id, safe=""),
            query={"format": "full"},
        )
        return {"message": _normalize_message(raw)}

    def create_draft(
        self,
        *,
        message: Mapping[str, Any],
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        raw = self._request_json(
            "POST",
            "/drafts",
            body={"message": {"raw": self._raw_message(message, request_id=request_id)}},
        )
        draft_id = raw.get("id")
        raw_message = raw.get("message")
        message_id = raw_message.get("id") if isinstance(raw_message, Mapping) else None
        if not isinstance(draft_id, str) or not draft_id:
            raise GoogleGmailTransportError("Gmail draft response lacks id")
        return {
            "draft_id": draft_id,
            "message_id": message_id if isinstance(message_id, str) else None,
            "upstream_reference": "gmail:draft:" + draft_id,
        }

    def send(
        self,
        *,
        message: Mapping[str, Any],
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        raw = self._request_json(
            "POST",
            "/messages/send",
            body={"raw": self._raw_message(message, request_id=request_id)},
        )
        message_id = raw.get("id")
        thread_id = raw.get("threadId")
        if not isinstance(message_id, str) or not message_id:
            raise GoogleGmailTransportError("Gmail send response lacks message id")
        return {
            "message_id": message_id,
            "thread_id": thread_id if isinstance(thread_id, str) else None,
            "upstream_reference": "gmail:message:" + message_id,
        }

    def archive(
        self,
        *,
        message_id: str,
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        raw = self._request_json(
            "POST",
            "/messages/" + quote(message_id, safe="") + "/modify",
            body={"removeLabelIds": ["INBOX"]},
        )
        returned_id = raw.get("id")
        if returned_id != message_id:
            raise GoogleGmailTransportError("Gmail archive response binds a different message")
        labels = raw.get("labelIds", [])
        if isinstance(labels, list) and "INBOX" in labels:
            raise GoogleGmailTransportError("Gmail archive response still contains INBOX label")
        return {
            "message_id": message_id,
            "archived": True,
            "upstream_reference": "gmail:message:" + message_id,
        }

    def _find_by_request_message_id(self, *, request_id: str) -> Mapping[str, Any] | None:
        message_id_header = _message_id_for_request(request_id)
        raw = self._request_json(
            "GET",
            "/messages",
            query={"q": "rfc822msgid:" + message_id_header, "maxResults": 2},
        )
        messages = raw.get("messages")
        if not isinstance(messages, list) or not messages:
            return None
        ids = [item.get("id") for item in messages if isinstance(item, Mapping) and isinstance(item.get("id"), str)]
        if len(ids) != 1:
            raise GoogleGmailTransportError("Gmail reconciliation found ambiguous request identity")
        return {
            "message_id": ids[0],
            "upstream_reference": "gmail:message:" + ids[0],
        }

    def reconcile(
        self,
        *,
        action: str,
        request_id: str,
        idempotency_key: str,
        operation: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        if action in (GMAIL_DRAFT_ACTION, GMAIL_SEND_ACTION):
            found = self._find_by_request_message_id(request_id=request_id)
            if found is None:
                return None
            if action == GMAIL_DRAFT_ACTION:
                # messages.list does not return draft resource ids. Returning None is
                # safer than claiming a draft receipt from only a message identity.
                return None
            return found
        if action == GMAIL_ARCHIVE_ACTION:
            message_id = operation.get("message_id")
            if not isinstance(message_id, str) or not message_id:
                raise GoogleGmailTransportError("archive reconciliation lacks message_id")
            raw = self._request_json(
                "GET",
                "/messages/" + quote(message_id, safe=""),
                query={"format": "minimal"},
            )
            labels = raw.get("labelIds", [])
            if not isinstance(labels, list):
                raise GoogleGmailTransportError("archive reconciliation response lacks labels")
            if "INBOX" in labels:
                return None
            return {
                "message_id": message_id,
                "archived": True,
                "upstream_reference": "gmail:message:" + message_id,
            }
        raise GoogleGmailTransportError("unsupported mutation reconciliation action")
