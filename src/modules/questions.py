from __future__ import annotations

import re


QUESTION_CUES = re.compile(
    r"[？?]|(什么|哪些|怎么|如何|为什么|是否|能否|能不能|请.{0,8}(介绍|说|讲)|"
    r"说说|讲讲|谈谈|介绍一下|了解多少|区别|差异|原理|流程|作用|优缺点|"
    r"你对|你会|你用过|你的|有没有|举个例子|谈一谈|"
    r"讲一下|说一下|基础数据类型|面向对象|多线程|索引|事务)"
)


def looks_like_question(text: str) -> bool:
    normalized = text.strip()
    return len(normalized) >= 4 and bool(QUESTION_CUES.search(normalized))


def context_for(question: str) -> str:
    """Use personal context only for explicit job or experience questions."""
    job = bool(re.search(r"岗位|职位|应聘|招聘|这份工作|我们公司|贵公司|公司业务", question))
    resume = bool(
        re.search(
            r"自我介绍|介绍一下自己|简历|你的经历|你的经验|你做过|你参与|"
            r"你负责|你的项目|项目经历|你在项目|结合.{0,12}(经历|项目)|"
            r"你为什么|你的优势|你的背景|"
            r"[你我](?:的)?专业|所学专业|专业背景|教育背景|学历|所学课程|"
            r"[你我](?:的)?(?:技能|能力|知识|技术背景|学习经历)|你学过|你掌握",
            question,
        )
    )
    if job and resume:
        return "both"
    if job:
        return "job"
    if resume:
        return "resume"
    return "none"
