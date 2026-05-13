from prompt_builder import build_prompt


def test_build_prompt_basic():
    result = build_prompt(
        biz_type="marketing",
        system_prompt="你是营销助手",
        user_input="我想了解产品",
        memory_block="",
        rag_block="",
        turn_history=[],
    )
    assert "你是营销助手" in result
    assert "我想了解产品" in result


def test_build_prompt_with_memory():
    result = build_prompt(
        biz_type="marketing",
        system_prompt="你是营销助手",
        user_input="你好",
        memory_block="## 用户记忆\n- 偏好: 周末联系",
        rag_block="",
        turn_history=[],
    )
    assert "偏好: 周末联系" in result


def test_build_prompt_with_rag():
    result = build_prompt(
        biz_type="marketing",
        system_prompt="你是营销助手",
        user_input="产品怎么样",
        memory_block="",
        rag_block="## 参考话术\n1. 产品优势介绍（相关度: 0.95）\n   我们的产品具有...",
        turn_history=[],
    )
    assert "参考话术" in result
    assert "产品优势" in result


def test_build_prompt_with_history():
    result = build_prompt(
        biz_type="customer_service",
        system_prompt="你是客服",
        user_input="谢谢",
        memory_block="",
        rag_block="",
        turn_history=[
            {"role": "user", "text": "你好"},
            {"role": "assistant", "text": "您好，请问有什么可以帮您？"},
        ],
    )
    assert "你好" in result
    assert "谢谢" in result
