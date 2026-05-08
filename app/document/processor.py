from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


class DocumentProcessor:
    """文档分块处理器"""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", ".", " ", ""],
            length_function=len,
        )

    def split(self, documents: List[Document]) -> List[Document]:
        """将文档列表切分为适合向量化的文本块"""
        chunks = self.splitter.split_documents(documents)
        for i, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = i
        return chunks

    def split_text(self, text: str, metadata: dict = None) -> List[Document]:
        """将纯文本切分为文档块"""
        doc = Document(page_content=text, metadata=metadata or {})
        return self.split([doc])
