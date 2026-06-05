import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from dsk.api import DeepSeekAPI, DeepSeekError

DEFAULT_MODEL = "deepseek-chat"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    web_search: bool = Field(default=False, alias="search_enabled")
    thinking: bool = Field(default=False, alias="thinking_enabled")


class ResponsesInputItem(BaseModel):
    role: str = "user"
    content: Any


class ResponsesRequest(BaseModel):
    model: str = DEFAULT_MODEL
    input: Any
    stream: bool = False
    temperature: Optional[float] = None
    max_output_tokens: Optional[int] = None


app = FastAPI(title="deepseek4free OpenAI-compatible API")


def read_env_file_value(name: str) -> Optional[str]:
    env_path = Path(__file__).with_name('.env')
    if not env_path.exists():
        return None
    try:
        for line in env_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            if key.strip() == name:
                return value.strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def require_api_key(authorization: Optional[str]) -> Optional[JSONResponse]:
    expected = os.getenv("OPENAI_API_KEY") or read_env_file_value("OPENAI_API_KEY")
    if not expected:
        return None
    if not authorization or not authorization.startswith("Bearer "):
        return error_response("Missing bearer token", 401, "authentication_error")
    provided = authorization.removeprefix("Bearer ").strip()
    if provided != expected:
        return error_response("Invalid API key", 401, "authentication_error")
    return None


def get_api() -> DeepSeekAPI:
    token = os.getenv("DEEPSEEK_AUTH_TOKEN")
    if not token:
        raise HTTPException(status_code=500, detail="DEEPSEEK_AUTH_TOKEN env is required")
    return DeepSeekAPI(token)


def build_prompt(messages: List[ChatMessage]) -> str:
    parts = []
    for m in messages:
        role = m.role.lower()
        if role == "system":
            parts.append(f"System: {m.content}")
        elif role == "assistant":
            parts.append(f"Assistant: {m.content}")
        else:
            parts.append(f"User: {m.content}")
    return "\n".join(parts)


def error_response(message: str, code: int = 500, err_type: str = "api_error") -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={"error": {"message": message, "type": err_type, "code": code}},
    )


def openai_chunk(
    completion_id: str,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


@app.get("/")
def root() -> Dict[str, str]:
    return {"name": "deepseek4free-openai-api", "status": "ok"}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/models")
def list_models() -> Dict[str, Any]:
    now = int(time.time())
    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model",
                "created": now,
                "owned_by": "deepseek4free",
            }
        ],
    }


def run_completion(model: str, prompt: str, stream: bool, thinking: bool = False, web_search: bool = False):
    api = get_api()
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"

    try:
        chat_id = api.create_chat_session()
    except DeepSeekError as e:
        return error_response(str(e), 502, "upstream_error")

    def generate_text() -> str:
        text_parts = []
        for chunk in api.chat_completion(
            chat_id,
            prompt,
            thinking_enabled=thinking,
            search_enabled=web_search,
        ):
            if chunk.get("type") == "text" and chunk.get("content"):
                text_parts.append(chunk["content"])
        return "".join(text_parts)

    if not stream:
        try:
            text = generate_text()
        except DeepSeekError as e:
            return error_response(str(e), 502, "upstream_error")
        return {
            "id": completion_id,
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    def sse_stream():
        try:
            yield "data: " + json.dumps(openai_chunk(completion_id, model, {"role": "assistant"})) + "\n\n"
            for chunk in api.chat_completion(
                chat_id,
                prompt,
                thinking_enabled=thinking,
                search_enabled=web_search,
            ):
                if chunk.get("type") == "text" and chunk.get("content"):
                    yield "data: " + json.dumps(
                        openai_chunk(completion_id, model, {"content": chunk["content"]}),
                        ensure_ascii=False,
                    ) + "\n\n"
            yield "data: " + json.dumps(openai_chunk(completion_id, model, {}, "stop")) + "\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield "data: " + json.dumps({"error": {"message": str(e), "type": "stream_error"}}) + "\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(sse_stream(), media_type="text/event-stream")


@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest, authorization: Optional[str] = Header(default=None)):
    auth_error = require_api_key(authorization)
    if auth_error:
        return auth_error
    if not req.messages:
        return error_response("messages is required", 400, "invalid_request_error")
    prompt = build_prompt(req.messages)
    return run_completion(req.model, prompt, req.stream, req.thinking, req.web_search)


def responses_input_to_messages(value: Any) -> List[ChatMessage]:
    if isinstance(value, str):
        return [ChatMessage(role="user", content=value)]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(ChatMessage(role="user", content=item))
            elif isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") in {"input_text", "text"}:
                            text_parts.append(block.get("text", ""))
                    content = "\n".join([p for p in text_parts if p])
                out.append(ChatMessage(role=role, content=str(content)))
        return out
    raise HTTPException(status_code=400, detail="input must be string or list")


@app.post("/v1/responses")
def responses(req: ResponsesRequest, authorization: Optional[str] = Header(default=None)):
    auth_error = require_api_key(authorization)
    if auth_error:
        return auth_error
    messages = responses_input_to_messages(req.input)
    if not messages:
        return error_response("input is required", 400, "invalid_request_error")
    prompt = build_prompt(messages)
    result = run_completion(req.model, prompt, req.stream)
    if req.stream:
        return result
    if isinstance(result, JSONResponse):
        return result
    text = result["choices"][0]["message"]["content"]
    return {
        "id": f"resp-{uuid.uuid4().hex}",
        "object": "response",
        "created_at": int(time.time()),
        "model": req.model,
        "status": "completed",
        "output": [
            {
                "id": f"msg-{uuid.uuid4().hex}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text, "annotations": []}],
            }
        ],
        "output_text": text,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }
