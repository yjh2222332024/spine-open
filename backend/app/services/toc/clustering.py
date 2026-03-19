"""
Spine-RAPTOR: Clustering Engine
================================
负责将多文档的章节摘要进行语义聚类，为递归摘要提供逻辑分组。

Author: Yan Junhao (严俊皓)
Architecture: Genius Architect Mode
"""

import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
import logging

class SpineClusteringEngine:
    """
    【级联聚类引擎】：支持多策略聚类，处理大规模文档章节归类。
    """
    
    def __init__(self, method: str = "gmm", max_clusters: int = 10):
        self.method = method
        self.max_clusters = max_clusters
        self.logger = logging.getLogger("SpineClustering")

    def perform_clustering(
        self, 
        embeddings: np.ndarray, 
        nodes: List[Dict[str, Any]]
    ) -> List[List[Dict[str, Any]]]:
        """
        根据向量相似度将节点划分为多个语义集群。
        """
        if len(nodes) <= 1:
            return [nodes]

        # 动态计算聚类数量 (平方根法则或硬上限)
        n_clusters = min(self.max_clusters, int(np.sqrt(len(nodes))) + 1)
        
        if self.method == "gmm":
            return self._cluster_gmm(embeddings, nodes, n_clusters)
        else:
            return self._cluster_kmeans(embeddings, nodes, n_clusters)

    def _cluster_gmm(
        self, 
        embeddings: np.ndarray, 
        nodes: List[Dict[str, Any]], 
        n_clusters: int
    ) -> List[List[Dict[str, Any]]]:
        """
        使用高斯混合模型 (GMM) 进行软聚类（允许节点属于多个语义中心，RAPTOR 核心思想）。
        """
        # 降维以提高稳定性 (简单处理，实际可引入 UMAP)
        gmm = GaussianMixture(n_components=n_clusters, random_state=42)
        gmm.fit(embeddings)
        
        # 获取每个节点属于各聚类的概率
        probs = gmm.predict_proba(embeddings)
        
        clusters = [[] for _ in range(n_clusters)]
        # RAPTOR 优化：如果概率 > 阈值，节点可以进入多个聚类，防止逻辑断裂
        threshold = 1.0 / n_clusters
        
        for idx, node_probs in enumerate(probs):
            for cluster_idx, prob in enumerate(node_probs):
                if prob > threshold:
                    clusters[cluster_idx].append(nodes[idx])
        
        # 过滤掉空聚类
        return [c for c in clusters if len(c) > 0]

    def _cluster_kmeans(
        self, 
        embeddings: np.ndarray, 
        nodes: List[Dict[str, Any]], 
        n_clusters: int
    ) -> List[List[Dict[str, Any]]]:
        """
        使用 K-Means 进行硬聚类。
        """
        kmeans = KMeans(n_components=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)
        
        clusters = [[] for _ in range(n_clusters)]
        for idx, label in enumerate(labels):
            clusters[label].append(nodes[idx])
            
        return [c for c in clusters if len(c) > 0]

    def summarize_cluster_stats(self, clusters: List[List[Dict[str, Any]]]):
        """打印聚类效能分析"""
        self.logger.info(f"Successfully generated {len(clusters)} semantic clusters.")
        for i, c in enumerate(clusters):
            titles = [n.get('title', 'Untitled')[:20] for n in c[:3]]
            self.logger.info(f"  Cluster {i}: {len(c)} nodes. (Sample: {titles}...)")

# 导出实例
clustering_engine = SpineClusteringEngine()
