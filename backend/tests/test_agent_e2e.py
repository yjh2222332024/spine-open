import os
import asyncio
from app.agents.graph import create_document_graph
from app.agents.state import DocumentState

async def run_agent_e2e():
    # 1. 准备测试文件
    test_pdf = "backend/temp_uploads/c44bf5f8-e8d9-42fa-9e7b-bdf361030194.pdf"
    if not os.path.exists(test_pdf):
        print(f"Error: Test PDF {test_pdf} not found.")
        return

    # 2. 初始化状态
    initial_state = DocumentState(
        file_path=test_pdf,
        document_type=None,
        total_pages=0,
        pages=[],
        raw_toc=[],
        structured_toc=[],
        processing_errors=[],
        confidence_score=0.0,
        current_node=None,
        instructions=[],
        retry_count=0,
        max_retries=3,
        metadata={}
    )

    # 3. 创建并运行图
    print(f"--- Starting SpineDoc Agent E2E for: {test_pdf} ---")
    app = create_document_graph()
    
    # 使用 ainvoke 异步运行 (LangGraph 推荐)
    final_state = await app.ainvoke(initial_state)
    
    print("\n--- E2E Run Completed ---")
    print(f"Final Node: {final_state.get('current_node')}")
    print(f"Document Type: {final_state.get('document_type')}")
    print(f"Final Confidence: {final_state.get('confidence_score')}")
    print(f"TOC Items: {len(final_state.get('structured_toc', []))}")
    print(f"Status: {final_state.get('metadata', {}).get('status')}")
    
    if final_state.get('processing_errors'):
        print(f"Errors: {final_state['processing_errors']}")

if __name__ == "__main__":
    asyncio.run(run_agent_e2e())
