from typing import List, Tuple, Dict, Any
from engines.base import ChatEngine

class RagEngine(ChatEngine):
    """
    A RAG-based chat engine that implements the ChatEngine protocol (Strategy Pattern).
    Responsible for executing queries through the LangChain retrieval-QA pipeline and 
    formatting history/citations for the Streamlit UI.
    """
    def __init__(self, rag_chain_with_history, history_store: Dict[str, Any]):
        """
        Initializes the RAG Engine with the configured pipeline.
        
        Args:
            rag_chain_with_history (RunnableWithMessageHistory): The LangChain conversational RAG chain.
            history_store (Dict): Store mapping session IDs to ChatMessageHistory.
        """
        self.chain = rag_chain_with_history
        self.history_store = history_store # maps session_id -> ChatMessageHistory
        self.last_sources: Dict[str, List[Dict[str, Any]]] = {} # session_id -> list of citations

    def answer(self, session_id: str, question: str) -> str:
        """
        Queries the RAG pipeline with history context and returns the text response.
        
        Args:
            session_id (str): The unique session key to scope chat memory and retrieval.
            question (str): The user query prompt.
            
        Returns:
            str: The model's generated answer text.
        """
        # Invoke the chain using 'input' as the input query key
        resp = self.chain.invoke(
            {"input": question},
            config={"configurable": {"session_id": session_id}},
        )
        
        # Extract and format the retrieved context documents (citations) for the UI
        context_docs = resp.get("context", [])
        self.last_sources[session_id] = [
            {
                "source": doc.metadata.get("source", "Unknown"),
                "page": doc.metadata.get("page", 0) + 1,  # Convert 0-indexed page to 1-indexed
                "content": doc.page_content
            }
            for doc in context_docs
        ]
        
        # Extract and return the answer text
        if isinstance(resp, dict):
            return resp.get("answer", "")
        return str(resp)

    def get_history(self, session_id: str) -> List[Tuple[str, str]]:
        """
        Retrieves the conversation history for the session, formatted as list of (role, message) tuples.
        
        Args:
            session_id (str): The active session identifier.
            
        Returns:
            List[Tuple[str, str]]: The chat history list.
        """
        h = self.history_store.get(session_id)
        if not h:
            return []
        
        # Translate LangChain messages (HumanMessage/AIMessage) into the required (role, content) strategy format
        return [
            ("user", m.content) if m.type == "human" else ("assistant", m.content)
            for m in h.messages
        ]

    def get_last_sources(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the database sources/citations generated during the last query execution.
        
        Args:
            session_id (str): The active session identifier.
            
        Returns:
            List[Dict]: A list of dictionary objects detailing source filename, page, and chunk text.
        """
        return self.last_sources.get(session_id, [])
