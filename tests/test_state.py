from halctf.client.base import ChatMessage, ToolCall
from halctf.loop.state import RunState


def test_short_history_passed_verbatim():
    st = RunState(system_prompt="S", task_prompt="T")
    st.add(ChatMessage(role="assistant", content="a1"))
    msgs = st.build_messages(keep_last=8)
    # system + user(task) + 1 履歴
    assert msgs[0].role == "system"
    assert msgs[1].content == "T"
    assert msgs[-1].content == "a1"


def test_long_history_is_compressed():
    st = RunState(system_prompt="S", task_prompt="T")
    for i in range(20):
        st.add(
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=[ToolCall(id=str(i), name="recon", arguments={"i": i})],
            )
        )
        st.add(ChatMessage(role="tool", content=f"result {i}", name="recon"))
    msgs = st.build_messages(keep_last=4)
    # 要約メッセージが挿入され、全 40 メッセージは渡らない
    assert any("経緯の要約" in m.content for m in msgs)
    assert len(msgs) < 40
