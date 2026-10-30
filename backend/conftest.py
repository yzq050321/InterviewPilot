"""pytest 全局配置：在导入 app 之前注入测试环境变量。

为什么需要这个文件
------------------
项目里有几处在 **模块导入时** 就读取环境变量，缺了会直接抛异常：

- ``app/database.py``        -> 读 ``DB_PASSWORD``，缺失时 ``raise ValueError``
- ``app/services/model_client.py`` -> ``os.environ["DEEPSEEK_API_KEY"]``（KeyError）
- ``app/services/rag_service.py``  -> ``os.environ["DASHSCOPE_API_KEY"]``（KeyError）

于是「有没有 .env」会决定测试能不能开始跑。本地靠手工 ``cp .env.example .env``
可以绕过，但 CI 是一台干净机器，没有 .env —— 必须让 ``pytest`` 零配置可运行。

这里统一注入假值。全部是测试用占位，不会发起真实请求：
测试里对模型的调用都用 monkeypatch 替换掉了。

用 ``setdefault`` 而不是直接赋值，是为了不覆盖本地 .env 里已有的真实配置。
"""

import os

_TEST_ENV = {
    # DeepSeek（假 key，测试中不会真正调用）
    "DEEPSEEK_API_KEY": "test-deepseek-key",
    "DEEPSEEK_MODEL": "deepseek-chat",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    # DashScope Embedding（假 key）
    "DASHSCOPE_API_KEY": "test-dashscope-key",
    "DASHSCOPE_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    # MySQL：只用于构造连接串，测试全程使用 SQLite 覆盖，不会真正连接
    "DB_USER": "interview_app",
    "DB_PASSWORD": "test-db-password",
    "DB_HOST": "127.0.0.1",
    "DB_PORT": "3306",
    "DB_NAME": "interview_pilot",
    # 鉴权：密码哈希是真实 bcrypt 格式，便于登录相关用例校验
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD_HASH": "$2b$04$zubgZYymDszmh/nYh1fIFO9snA2J/pcMLNqjEwQQwzH51QapHaMfq",
    "ADMIN_JWT_SECRET": "test-jwt-secret-at-least-32-bytes-long!!",
    "DEMO_USERNAME": "demo",
    "DEMO_PASSWORD_HASH": "$2b$04$PUh7Ph1GyuJuYz0uefuQW.AB47lHZifwQgcmsRoDtnAhq6BoAEpRq",
    "HR_SIGNUP_INVITE_CODE": "test-invite-code",
    # 用量记录默认关闭，避免测试往家目录写 JSONL
    "MODEL_USAGE_ENABLED": "0",
}

for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)
