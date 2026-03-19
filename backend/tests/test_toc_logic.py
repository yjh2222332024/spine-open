import pytest
from app.services.toc.base import TOCStrategy
from app.services.toc.manager import TOCManager
from typing import List, Dict, Any

class MockConflictStrategy(TOCStrategy):
    """一个模拟冲突的策略：强制将所有 L1 节点改为 L2"""
    def process(self, raw_items: List[Dict[str, Any]], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        for item in raw_items:
            if item.get("level") == 1:
                context["conflicts"].append({
                    "id": item["id"], 
                    "msg": "Level conflict: Strategy A says 1, Strategy B says 2"
                })
                item["level"] = 2
        return raw_items

def test_toc_manager_di_and_conflicts():
    # 原始测试数据 (散沙)
    raw_data = [
        {"id": "1", "title": "Chapter 1", "page": 5, "level": 1},
        {"id": "2", "title": "Section 1.1", "page": 6, "level": 2}
    ]
    
    # 注入模拟冲突策略
    manager = TOCManager(strategies=[MockConflictStrategy()])
    
    # 执行构建
    tree = manager.build_tree(raw_data)
    
    # 验证 1：策略是否生效
    assert tree[0]["level"] == 2
    
    # 验证 2：冲突是否被捕捉 (生产预警机制)
    conflicts = manager.get_conflict_report()
    print(f"\nConflict Report: {conflicts}")
    assert len(conflicts) > 0
    assert "Level conflict" in conflicts[0]["msg"]
    
    # 验证 3：树形父子关系
    # 因为都被改成了 L2，所以 Chapter 1 不再是 Section 1.1 的父节点
    assert tree[1]["parent_id"] is None

if __name__ == "__main__":
    test_toc_manager_di_and_conflicts()
