"""智能外呼 Orchestrator 入口 - 异步初始化 + 全组件集成"""
import logging
from fs_esl import ESLEventLoop
from event_handlers import EventDispatcher
from call_state import CallStateManager
from fs_actions import FSActions
from graph_flow import create_call_graph, set_memory_assembler
from memory.assembler import MemoryAssembler
from mcp_client import MCPClient
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== 智能外呼 Orchestrator 启动 ===")

    # 初始化记忆聚合器
    assembler = MemoryAssembler()
    set_memory_assembler(assembler)

    # 编译 LangGraph（一次编译，复用）
    graph = create_call_graph()
    logger.info("LangGraph 编译完成")

    # MCP 客户端
    mcp_client = MCPClient(settings.mcp_server_url)

    # ESL 事件循环
    state_mgr = CallStateManager()
    loop = ESLEventLoop(settings.fs_esl_host, settings.fs_esl_port, settings.fs_esl_password)
    if not loop.connect():
        logger.error("初始连接失败，将在循环中重连")

    actions = FSActions(loop.conn)
    dispatcher = EventDispatcher(
        state_mgr=state_mgr,
        conn=loop.conn,
        actions=actions,
        graph=graph,
        mcp_client=mcp_client,
    )

    try:
        loop.run(dispatcher)
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭...")
        loop.stop()


if __name__ == "__main__":
    main()
