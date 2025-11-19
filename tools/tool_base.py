from abc import ABC, abstractmethod

class BaseTool(ABC):
    """모든 Tool의 공통 인터페이스"""

    @abstractmethod
    def invoke(self, text: str) -> str:
        """텍스트 입력을 받아 실제 작업 수행 후 결과 반환"""
        ...