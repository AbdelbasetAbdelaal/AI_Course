import yaml
from typing import Dict, Any, Tuple
try:
    # Try importing from the newer modularized langchain_classic structure
    from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
    from langchain_classic.chains.combine_documents import create_stuff_documents_chain
except ImportError:
    # Fallback to standard langchain module if classic is not installed
    from langchain.chains import create_history_aware_retriever, create_retrieval_chain
    from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_chroma import Chroma

def load_config(config_path: str = "config.yaml") -> dict:
    """
    Loads application parameters and hyperparameters from the configuration YAML file.
    
    Args:
        config_path (str): The filename/path of the config file. Resolves to the absolute
                           project directory if a relative path is passed.
                           
    Returns:
        dict: The parsed configuration settings.
    """
    # Dynamically resolve relative pathing to absolute project root directory coords
    if config_path == "config.yaml" or config_path is None:
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(script_dir), "config.yaml")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

def get_llm(provider: str, api_key: str, config: dict, model_name: str = None):
    """
    Dynamically loads and returns the configured LLM client based on the selected provider.
    
    Args:
        provider (str): The selected LLM service (Groq, OpenAI, or Gemini).
        api_key (str): The user-provided secret API key.
        config (dict): The configuration settings dict.
        model_name (str, optional): Overrides the default model configured in config.yaml.
        
    Returns:
        BaseChatModel: An instance of the requested LangChain chat model wrapper.
    """
    # Load model and temperature from config
    llm_cfg = config.get("llm", {}).get(provider.lower(), {})
    if not model_name:
        model_name = llm_cfg.get("model_name")
    temperature = llm_cfg.get("temperature", 0.0)

    # 1. Initialize Groq Chat Client
    if provider.lower() == "groq":
        try:
            from langchain_groq import ChatGroq
        except ImportError:
            raise ImportError("The 'langchain-groq' package is required for Groq. Please run `pip install langchain-groq`.")
        return ChatGroq(
            api_key=api_key,
            model=model_name,
            temperature=temperature
        )
        
    # 2. Initialize OpenAI Chat Client
    elif provider.lower() == "openai":
        try:
            from langchain_openai import ChatOpenAI
        except ImportError:
            raise ImportError("The 'langchain-openai' package is required for OpenAI. Please run `pip install langchain-openai`.")
        return ChatOpenAI(
            api_key=api_key,
            model=model_name,
            temperature=temperature
        )
        
    # 3. Initialize Google Gemini Chat Client
    elif provider.lower() == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError("The 'langchain-google-genai' package is required for Gemini. Please run `pip install langchain-google-genai`.")
        return ChatGoogleGenerativeAI(
            google_api_key=api_key,
            model=model_name,
            temperature=temperature
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")

def create_conversational_rag_chain(
    vector_store: Chroma,
    provider: str,
    api_key: str,
    model_name: str = None,
    config_path: str = "config.yaml"
) -> Tuple[RunnableWithMessageHistory, Dict[str, ChatMessageHistory]]:
    """
    Constructs the RAG pipeline combining:
      1. An LLM initialization step.
      2. A history-aware query reformulation retriever.
      3. A document-stuffing QA chain.
      4. A conversational session-based memory wrapper.
      
    Args:
        vector_store (Chroma): The indexed vector store to retrieve chunks from.
        provider (str): LLM provider string.
        api_key (str): Secret API credentials.
        model_name (str, optional): Custom model identifier.
        config_path (str): Yaml configurations directory.
        
    Returns:
        Tuple: (RunnableWithMessageHistory chain, history_store mapping session IDs)
    """
    config = load_config(config_path)
    
    # 1. Initialize LLM Client
    llm = get_llm(provider, api_key, config, model_name)
    
    # 2. Configure vector store retriever (fetching top K documents)
    ret_cfg = config.get("retriever", {})
    k = ret_cfg.get("k", 4)
    search_type = ret_cfg.get("search_type", "similarity")
    
    search_kwargs = {"k": k}
    retriever = vector_store.as_retriever(
        search_type=search_type,
        search_kwargs=search_kwargs
    )
    
    # 3. Create History-Aware Retriever Prompt
    # This system prompt instructs the LLM to rewrite follow-up questions incorporating the context of prior messages
    # to form a standalone question suitable for document retrieval.
    contextualize_q_system_prompt = (
        "Given a chat history and the latest user question "
        "which might reference context in the chat history, "
        "formulate a standalone question which can be understood "
        "without the chat history. Do NOT answer the question, "
        "just reformulate it if needed and otherwise return it as is."
    )
    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", contextualize_q_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # Creates a chain that takes chat history and inputs, rewrites the input, and runs it through the retriever
    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_q_prompt
    )
    
    # 4. Create QA combined documents chain prompt
    # Instructs the LLM to answer the question using strictly the retrieved document context.
    qa_system_prompt = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise. Cite the sources at the end if relevant.\n\n"
        "Context:\n{context}"
    )
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    # Stuffing chain: bundles all retrieved document chunks and parses them directly into the context prompt parameter
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    
    # 5. Build final retrieval chain
    # Chains the rewritten query retriever and stuffing QA chain together
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    # 6. Session history memory storage (maps session_id -> ChatMessageHistory)
    history_store: Dict[str, ChatMessageHistory] = {}
    
    def get_session_history(session_id: str) -> ChatMessageHistory:
        if session_id not in history_store:
            history_store[session_id] = ChatMessageHistory()
        return history_store[session_id]
        
    # Wrap in conversational runner (handles loading and saving message states automatically)
    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        output_messages_key="answer"
    )
    
    return conversational_rag_chain, history_store
