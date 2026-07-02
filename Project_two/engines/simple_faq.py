from typing import List, Tuple, Dict
from engines.base import ChatEngine

class SimpleFAQEngine(ChatEngine):
    """
    A simple rule-based FAQ chat engine that implements the ChatEngine protocol.
    Used for backwards compatibility and basic fallback scenarios.
    """
    def __init__(self, faq_map: Dict[str, str] = None):
        self.faq_map = faq_map if faq_map is not None else {
            "hello": "Hello! I am a simple FAQ chatbot. How can I help you?",
            "what is RAG?": "Retrieval-Augmented Generation (RAG) is a technique that enhances LLM responses using external knowledge sources.",
            "bye": "Goodbye! Have a great day!"
        }
        # maps session_id -> list of (role, message) tuples
        self.histories: Dict[str, List[Tuple[str, str]]] = {}

    def answer(self, session_id: str, question: str) -> str:
        # Standardize question key mapping
        clean_question = question.strip().lower()
        ans = self.faq_map.get(clean_question, "Sorry, I don't know the answer to that. Please ask about RAG or say hello.")
        
        self.histories.setdefault(session_id, [])
        self.histories[session_id].append(("user", question))
        self.histories[session_id].append(("assistant", ans))
        return ans

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        return self.histories.get(session_id, [])
