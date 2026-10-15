from __future__ import annotations

import asyncio

from openai import AsyncOpenAI
from PyQt6.QtCore import QObject, pyqtSignal

from ..config.config import BASE_URL, MODEL, Profile
from .questions import context_for


class AnswerSignals(QObject):
    started = pyqtSignal()
    delta = pyqtSignal(str)
    done = pyqtSignal(str)
    error = pyqtSignal(str)


def build_messages(question: str, profile: Profile) -> list[dict[str, str]]:
    context_kind = context_for(question)
    context: list[str] = []
    if context_kind in ("job", "both"):
        if profile.job_title.strip():
            context.append(f"岗位名称：{profile.job_title.strip()}")
        if profile.company.strip():
            context.append(f"公司：{profile.company.strip()}")
        if profile.job_description.strip():
            context.append(f"岗位描述：{profile.job_description.strip()[:8000]}")
    if context_kind in ("resume", "both") and profile.resume_text.strip():
        context.append(f"候选人简历：{profile.resume_text.strip()[:16000]}")

    system = (
        "你是中文面试回答助手。只回答当前问题，先给简洁直接的答案，"
        "需要时再给两到三个要点。不要复述问题，不要编造个人经历、公司业务或岗位细节。"
        "一般知识题只依据知识回答，不主动关联候选人背景。"
        "当问题涉及候选人的专业、课程或技能时，先核对所提供的简历，准确说出已有事实，"
        "再说明它们与岗位职责的具体关联；不要把软件专业说成热力运行经验。"
        "简历已有的信息不得用占位符代替，也不要让候选人再次补充。"
        "只有资料确实没有提供回答所需的个人事实时，才说明需要补充什么。"
    )
    user = f"面试官的问题：{question.strip()}"
    if context:
        user += "\n\n仅在回答此问题确实相关时使用以下资料：\n" + "\n".join(context)
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


class AnswerService:
    def __init__(self, signals: AnswerSignals) -> None:
        self.signals = signals
        self._client: AsyncOpenAI | None = None
        self._task: asyncio.Task[None] | None = None

    def set_api_key(self, key: str) -> None:
        if self._client is not None:
            asyncio.create_task(self._client.close())
        self._client = AsyncOpenAI(api_key=key, base_url=BASE_URL, timeout=45.0)

    def answer(self, question: str, profile: Profile) -> None:
        self.cancel()
        self._task = asyncio.create_task(self._answer(question, profile))

    def cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()

    async def _answer(self, question: str, profile: Profile) -> None:
        if self._client is None:
            self.signals.error.emit("请先设置硅基流动 API Key。")
            return
        self.signals.started.emit()
        answer = ""
        try:
            stream = await self._client.chat.completions.create(
                model=MODEL,
                messages=build_messages(question, profile),  # type: ignore[arg-type]
                stream=True,
                max_tokens=450,
                extra_body={"enable_thinking": False},
            )
            try:
                async for chunk in stream:
                    if chunk.choices:
                        delta = chunk.choices[0].delta.content or ""
                        if delta:
                            answer += delta
                            self.signals.delta.emit(delta)
            finally:
                await stream.close()
            self.signals.done.emit(answer)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.signals.error.emit(f"回答失败：{exc}")

    async def close(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._client is not None:
            await self._client.close()
