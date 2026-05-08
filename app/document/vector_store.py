from typing import List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.config import settings


class VectorStoreManager:
    """向量数据库管理器"""

    def __init__(self):
        # 使用本地 sentence-transformers 做 embedding (无需API费用)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self._client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._vectorstore: Optional[Chroma] = None

    @property
    def vectorstore(self) -> Chroma:
        if self._vectorstore is None:
            self._vectorstore = Chroma(
                collection_name=settings.CHROMA_COLLECTION,
                embedding_function=self.embeddings,
                client=self._client,
            )
        return self._vectorstore

    def add_documents(self, documents: List[Document]) -> int:
        """添加文档块到向量库，返回添加的块数"""
        if not documents:
            return 0
        ids = self.vectorstore.add_documents(documents)
        return len(ids)

    def search(
        self,
        query: str,
        top_k: int = settings.TOP_K_RETRIEVAL,
        filter_meta: Optional[dict] = None,
    ) -> List[Document]:
        """语义检索返回最相关的文档块"""
        return self.vectorstore.similarity_search(
            query, k=top_k, filter=filter_meta,
        )

    def delete_by_source(self, source_path: str) -> int:
        """按源文件路径删除文档（用于更新）"""
        collection = self.vectorstore._collection
        results = collection.get(where={"source": source_path})
        ids = results.get("ids", [])
        if isinstance(ids, list) and ids:
            # Handle both list of ids and nested list
            flat_ids = []
            for item in ids:
                if isinstance(item, list):
                    flat_ids.extend(item)
                else:
                    flat_ids.append(item)
            if flat_ids:
                collection.delete(ids=flat_ids)
        return len(ids) if isinstance(ids, list) else 0

    def get_document_count(self) -> int:
        return self.vectorstore._collection.count()

    def list_sources(self) -> List[str]:
        collection = self.vectorstore._collection
        result = collection.get()
        metadatas = result.get("metadatas", [])
        if not metadatas:
            return []
        sources = set()
        for meta in metadatas:
            src = meta.get("source", "")
            if src:
                sources.add(src)
        return sorted(sources)
