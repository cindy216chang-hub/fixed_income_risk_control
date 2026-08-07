import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# 固定讀取專案根目錄的 .env。
load_dotenv(dotenv_path=ENV_PATH)


# Gemini 必須依照這個 JSON 結構回傳資料。
KNOWLEDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string"
                    },
                    "category": {
                        "type": "string"
                    },
                    "aliases": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "summary": {
                        "type": "string"
                    },
                    "definition": {
                        "type": "string"
                    },
                    "scope": {
                        "type": "string"
                    },
                    "trigger": {
                        "type": "string"
                    },
                    "workflow": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "deadlines": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "responsible_roles": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "important_rules": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "related_topics": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "source_pages": {
                        "type": "array",
                        "items": {
                            "type": "integer"
                        }
                    }
                },
                "required": [
                    "title",
                    "category",
                    "aliases",
                    "summary",
                    "definition",
                    "scope",
                    "trigger",
                    "workflow",
                    "deadlines",
                    "responsible_roles",
                    "important_rules",
                    "related_topics",
                    "source_pages"
                ]
            }
        }
    },
    "required": [
        "notes"
    ]
}


class GeminiClient:
    """使用 Google Gen AI SDK 呼叫 Gemini API。"""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.1-flash-lite",
        ).strip()

        if not self.api_key:
            raise ValueError(
                "找不到 GEMINI_API_KEY。\n"
                f"程式預期讀取：{ENV_PATH}"
            )

        self.client = genai.Client(api_key=self.api_key)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> str:
        """呼叫 Gemini 並回傳一般文字。"""

        config_arguments = {
            "system_instruction": system_prompt,
        }

        if temperature is not None:
            config_arguments["temperature"] = temperature

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    **config_arguments
                ),
            )
        except Exception as error:
            raise RuntimeError(
                f"Gemini API 呼叫失敗：{error}"
            ) from error

        if not response.text:
            raise RuntimeError("Gemini API 回傳的答案是空白。")

        return response.text.strip()

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
    ) -> dict:
        """要求 Gemini 依照固定 Schema 回傳 JSON。"""

        config_arguments = {
            "system_instruction": system_prompt,
            "response_mime_type": "application/json",
            "response_json_schema": KNOWLEDGE_SCHEMA,
        }

        if temperature is not None:
            config_arguments["temperature"] = temperature

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    **config_arguments
                ),
            )
        except Exception as error:
            raise RuntimeError(
                f"Gemini API 呼叫失敗：{error}"
            ) from error

        if not response.text:
            raise RuntimeError("Gemini API 回傳的 JSON 是空白。")

        try:
            result = json.loads(response.text)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "Gemini 回傳內容無法解析成 JSON。\n"
                f"解析錯誤：{error}\n\n"
                f"原始內容：\n{response.text}"
            ) from error

        if not isinstance(result, dict):
            raise RuntimeError("Gemini 回傳的 JSON 最外層不是物件。")

        if "notes" not in result:
            raise RuntimeError("Gemini 回傳的 JSON 缺少 notes 欄位。")

        if not isinstance(result["notes"], list):
            raise RuntimeError("Gemini 回傳的 notes 不是陣列。")

        return result


def run_connection_test() -> None:
    """使用無機密文字測試 Gemini API。"""

    client = GeminiClient()

    answer = client.chat(
        system_prompt="你是 API 連線測試助理。",
        user_prompt="請只回答：API連線成功",
        temperature=0,
    )

    print("Gemini 連線成功。")
    print(f"模型：{client.model}")
    print(f"回答：{answer}")


if __name__ == "__main__":
    run_connection_test()