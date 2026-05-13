def build_prompt(
    biz_type: str,
    system_prompt: str,
    user_input: str,
    memory_block: str = "",
    rag_block: str = "",
    turn_history: list[dict] | None = None,
    max_history_turns: int = 10,
) -> str:
    parts = [system_prompt]

    if rag_block:
        parts.append(f"\n{rag_block}")

    if memory_block:
        parts.append(f"\n{memory_block}")

    if turn_history:
        recent = turn_history[-max_history_turns:]
        history_lines = []
        for turn in recent:
            role = "用户" if turn["role"] == "user" else "助手"
            history_lines.append(f"{role}: {turn['text']}")
        parts.append("\n## 对话历史\n" + "\n".join(history_lines))

    parts.append(f"\n用户: {user_input}")
    parts.append("\n请以JSON格式回复: {\"action\": \"...\", \"text\": \"...\", \"intent\": \"...\"}")

    return "\n".join(parts)
