from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """모든 Agent의 공통 인터페이스"""

    @abstractmethod
    def run(self, instruction: str) -> str:
        """사용자 입력을 받아 처리 후 결과 반환"""
        ...