from fastapi.testclient import TestClient
from types import SimpleNamespace

import main
from app.services import llm_service


from app.services import llm_service

from openai import APITimeoutError
client = TestClient(main.app)


def test_create_interview_timeout(monkeypatch):

    # 1. 定义假的 AI 生成函数

    def fake_generate_question(position, difficulty):
        raise APITimeoutError(request=None)

    # 2. 临时替换真实函数
    monkeypatch.setattr(
        main,
        "generate_question",
        fake_generate_question
    )

    # 3. 向 FastAPI 发送测试请求
    response = client.post(
        "/api/interviews",
        json={
            "position": "Python后端开发",
            "difficulty": "中等"
        }
    )

    # 4. 验证接口是否正确处理超时
    assert response.status_code == 504

    assert response.json()["detail"] == (
        "AI 服务响应超时，请稍后重试"
    )
    

def test_create_interview_empty_question(monkeypatch):

    # 模拟 AI 生成函数返回空字符串
    def fake_generate_question(position, difficulty):
        return ""

    # 替换路由中实际使用的生成函数
    monkeypatch.setattr(
        main,
        "generate_question",
        fake_generate_question
    )

    response = client.post(
        "/api/interviews",
        json={
            "position": "Python后端开发",
            "difficulty": "中等"
        }
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "AI 面试题生成失败"
    
def test_create_interview_empty_question(monkeypatch):

    class FakeChain:

        def invoke(self, inputs):
            return SimpleNamespace(
                content=""
            )


    monkeypatch.setattr(
        llm_service,
        "chain",
        FakeChain()
    )


    response = client.post(
        "/api/interviews",
        json={
            "position": "Python后端开发",
            "difficulty": "中等"
        }
    )


    assert response.status_code == 502

    assert response.json()["detail"] == (
        "AI 面试题生成失败"
    )