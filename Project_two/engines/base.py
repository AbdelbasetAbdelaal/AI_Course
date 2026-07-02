from typing import Protocol, List, Tuple

class ChatEngine(Protocol):
    """
    Protocol defining the stable interface for chat engines.
    """
    def answer(self, session_id: str, question: str) -> str:
        """
        Generate an answer for the given question in the context of the session_id.
        """
        ...

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        """
        Retrieve the conversation history for the given session_id as a list of (role, message) tuples.
        """
        ...

class Chatbot:
    """
    Façade class that delegates chat interactions to the configured ChatEngine.
    """
    def __init__(self, engine: ChatEngine):
        self.engine = engine

    def ask(self, session_id: str, question: str) -> str:
        """
        Ask a question and return the answer from the active engine.
        """
        return self.engine.answer(session_id, question)

    def history(self, session_id: str) -> List[Tuple[str, str]]:
        """
        Retrieve the active chat history for a session from the active engine.
        """
        return self.engine.get_history(session_id)
