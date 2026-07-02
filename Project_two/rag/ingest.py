import os
import shutil
import tempfile
import yaml
from typing import List, Any
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
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
    # If using the default relative filename, resolve it to the absolute project directory.
    # This prevents FileNotFoundError when running the app from different working directories.
    if config_path == "config.yaml" or config_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(script_dir), "config.yaml")
        
    with open(config_path, "r") as f:
        return yaml.safe_load(f)

class DocumentIngester:
    """
    Orchestrates the document ingestion pipeline.
    Responsible for:
      1. Parsing uploaded PDF files using PyPDFLoader.
      2. Splitting parsed document text into smaller, overlapping chunks using RecursiveCharacterTextSplitter.
      3. Creating vector representations using HuggingFaceEmbeddings.
      4. Storing and indexing vector representations in a persistent Chroma DB collection.
    """
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initializes the ingester with hyperparameters and settings loaded from config.yaml.
        """
        # Load configuration dictionary
        self.config = load_config(config_path)
        
        # Extract embedding model settings (defaults to 'all-MiniLM-L6-v2' on 'cpu')
        embed_cfg = self.config.get("embedding", {})
        model_name = embed_cfg.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
        device = embed_cfg.get("device", "cpu")
        
        # Instantiate HuggingFace embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device}
        )
        
        # Extract text splitter chunk parameters
        splitter_cfg = self.config.get("text_splitter", {})
        self.chunk_size = splitter_cfg.get("chunk_size", 1000)
        self.chunk_overlap = splitter_cfg.get("chunk_overlap", 200)
        
        # Extract vector store database path and collection configurations
        vs_cfg = self.config.get("vector_store", {})
        persist_dir = vs_cfg.get("persist_directory", ".chroma/student-rag")
        
        # Dynamically resolve relative persistence path to absolute project-root coordinates
        if not os.path.isabs(persist_dir):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            self.persist_directory = os.path.abspath(os.path.join(project_root, persist_dir))
        else:
            self.persist_directory = persist_dir
            
        self.collection_name = vs_cfg.get("collection_name", "pdf_qa_collection")

    def ingest_uploaded_files(self, uploaded_files: List[Any]) -> Chroma:
        """
        Processes a list of upload stream files, chunks their content,
        generates embeddings, and writes the representations to the Chroma index.
        
        Args:
            uploaded_files (list): A list of uploaded file-like streams (e.g. Streamlit UploadedFile).
            
        Returns:
            Chroma: The instantiated and updated Chroma vector store client.
        """
        all_documents = []
        
        # Create a temporary directory on the operating system to write uploaded files
        # so that LangChain's PyPDFLoader can access them via filesystem paths.
        temp_dir = tempfile.mkdtemp()
        try:
            for uploaded_file in uploaded_files:
                # Save stream file content temporarily to the disk
                temp_file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(temp_file_path, "wb") as f:
                    shutil.copyfileobj(uploaded_file, f)
                
                # Load PDF using PyPDFLoader
                loader = PyPDFLoader(temp_file_path)
                docs = loader.load()
                
                # Inject the original filename as metadata source (replaces the temp file path)
                for doc in docs:
                    doc.metadata["source"] = uploaded_file.name
                
                all_documents.extend(docs)
                
            # Verify that at least some text content was successfully loaded
            if not all_documents:
                raise ValueError("No text content could be extracted from the uploaded PDF(s).")
            
            # Initialize the text splitter (splits text on paragraphs, sentences, and words recursively)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                length_function=len
            )
            chunks = text_splitter.split_documents(all_documents)
            
            # Initialize or open the Chroma collection and index the documents
            vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.persist_directory
            )
            
            # Embed and insert chunks into the vector store
            vector_store.add_documents(chunks)
            return vector_store
            
        finally:
            # Clean up the temporary folder from the disk to free resources
            shutil.rmtree(temp_dir)

    def get_vector_store(self) -> Chroma:
        """
        Loads and returns the existing Chroma vector store client from the disk.
        
        Returns:
            Chroma: The persistent Chroma vector store database client.
        """
        return Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def clear_vector_store(self) -> None:
        """
        Deletes the Chroma collection metadata and completely resets the persistence directory on disk.
        """
        if os.path.exists(self.persist_directory):
            try:
                # Attempt to delete the collection programmatically through the client
                db = self.get_vector_store()
                db.delete_collection()
            except Exception:
                # Fallback to direct directory removal if database is uninitialized
                pass
            # Force remove directory from filesystem
            shutil.rmtree(self.persist_directory, ignore_errors=True)
