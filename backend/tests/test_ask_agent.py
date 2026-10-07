"""问答分两边：agent 问你（待拍板 D → 决定 A）· 你问 agent（问- → 答-）。
作者 2026-09-27：「我觉得问答需要两个模块，一个是agent不懂的问人，一个是人不懂的问机器人」。"""
import anyio
from fastapi.testclient import TestClient

import store
from main import create_app
from test_mcp import _call


def test_you_ask_the_agent_and_it_answers(proj):
    with TestClient(create_app(proj)) as client:
        assert client.post("/api/qa/ask", json={"text": " "}).status_code == 400
        q = client.post("/api/qa/ask", json={"text": "注意力为什么要除以根号 d？", "where": "文献 L1 第 3 页"}).json()
        assert q["code"] == "问-01" and q["detail"] == "文献 L1 第 3 页"
        qa = client.get("/api/qa").json()
        assert [x["code"] for x in qa["asked"]] == ["问-01"] and qa["asked"][0]["answer"] is None
        # 提问是操作日志，答案是问答记录；都不自动写入人的笔记。
        assert "问-01" not in [e["body"].split("：")[0] for e in client.get("/api/notes/总览").json()["entries"]]

    got = anyio.run(_call, proj, [
        ("get_overview", {}),
        ("answer_person", {"code": "问-01", "answer": "为了不让点积太大、softmax 太尖（原文第 4 页 3.2.1 节）。"}),
        ("answer_person", {"code": "问-01", "answer": "再答一次"}),
        ("get_overview", {}),
    ])
    assert "## 你问 agent：1 条等你答" in got[0] and "问-01 注意力为什么要除以根号 d？（出处：文献 L1 第 3 页）" in got[0]
    assert "答了 问-01（答-01）" in got[1] and got[2].startswith("没写上") and "你问 agent" not in got[3]
    c = store.connect(proj.db_path)
    q = store.list_asked(c)[0]
    c.close()
    assert q["closed_at"] and q["answer"]["code"] == "答-01" and q["answer"]["created_by"] == "agent:test-agent"
    assert "3.2.1" in q["answer"]["text"]
