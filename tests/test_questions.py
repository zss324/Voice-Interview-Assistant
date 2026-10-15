from src.config.config import Profile
from src.modules.questions import context_for, looks_like_question
from src.modules.service import build_messages


def test_general_question_has_no_personal_context():
    profile = Profile(job_title="Java 开发", resume_text="曾在甲公司做支付项目")
    messages = build_messages("Java 的基础数据类型有哪些？", profile)
    assert context_for("Java 的基础数据类型有哪些？") == "none"
    assert "Java 开发" not in str(messages)
    assert "支付项目" not in str(messages)


def test_explicit_job_and_resume_questions_use_only_relevant_context():
    profile = Profile(job_title="Java 开发", resume_text="曾在甲公司做支付项目")
    job = str(build_messages("你对这个岗位有什么了解？", profile))
    resume = str(build_messages("介绍一下你的项目经历", profile))
    assert "Java 开发" in job and "支付项目" not in job
    assert "支付项目" in resume and "Java 开发" not in resume


def test_job_and_personal_major_question_uses_both_contexts():
    question = "简单说一下你对该职位的了解，这个工作做什么，以及你的专业能对这个工作有什么用？"
    profile = Profile(
        job_title="热网运行工程师ZXLY/管理培训生",
        company="华润电力",
        job_description="监视换热站参数，分析蒸汽用户用热数据，维护办公网络设备。",
        resume_text="教育背景：软件工程硕士，软件工程本科。主修计算机网络、数据库。项目：智能 OnCall Agent。",
    )
    messages = build_messages(question, profile)
    assert context_for(question) == "both"
    assert "热网运行工程师" in messages[1]["content"]
    assert "软件工程硕士" in messages[1]["content"]
    assert "计算机网络" in messages[1]["content"]
    assert "简历已有的信息不得用占位符代替" in messages[0]["content"]


def test_only_questions_trigger_automatic_answers():
    assert looks_like_question("请介绍一下你自己")
    assert looks_like_question("Java 基础数据类型有哪些")
    assert not looks_like_question("今天是星期三")
