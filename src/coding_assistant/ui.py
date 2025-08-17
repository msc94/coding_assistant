from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import create_confirm_session


class UI:
    async def ask(self, prompt_text: str, default: Optional[str] = None) -> str:  # pragma: no cover - interface stub
        raise NotImplementedError

    async def confirm(self, prompt_text: str) -> bool:  # pragma: no cover - interface stub
        raise NotImplementedError


class PromptToolkitUI(UI):
    async def ask(self, prompt_text: str, default: Optional[str] = None) -> str:
        print(prompt_text)
        return await PromptSession().prompt_async("> ", default=default or "")

    async def confirm(self, prompt_text: str) -> bool:
        return await create_confirm_session(prompt_text).prompt_async()
