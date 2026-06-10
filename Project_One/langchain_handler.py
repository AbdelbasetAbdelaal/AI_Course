# Import LangChain modules for Gemini integration and structured data parsing
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class SearchParams(BaseModel):
    """Pydantic model used for extracting structured entities from natural language queries."""
    first_name: Optional[str] = Field(None, description="The first name of the person")
    last_name: Optional[str] = Field(None, description="The last name of the person")
    subject: Optional[str] = Field(None, description="The academic subject or class name")

class LangChainAssistant:
    """Wrapper class for managing interactions with Google's Gemini LLM via LangChain."""
    def __init__(self, api_key: str, db_config: Dict[str, Any] = None, is_admin: bool = False):
        self.model = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", # Using the latest flash model for speed
            google_api_key=api_key,
            temperature=0.7
        )
        self.is_admin = is_admin
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are the Elhawey School Assistant. Your role is to help students, parents, and staff. "
                "Be professional, polite, and encouraging."
            )),
            MessagesPlaceholder(variable_name="history"), # Injects previous chat messages
            ("user", "{input}"),
        ])
        
        # Define the processing chain: Prompt -> AI Model -> String Result
        self.chain = self.prompt | self.model | StrOutputParser()
        
        # Specialized model instance that returns structured SearchParams instead of strings
        self.extractor_model = self.model.with_structured_output(SearchParams)

        # Text-to-SQL Agent Setup
        self.sql_agent = None
        if db_config:
            try:
                from langchain_community.utilities import SQLDatabase
                from langchain_community.agent_toolkits import create_sql_agent
                
                # SQLAlchemy URI
                db_uri = f"mysql+mysqlconnector://{db_config.get('user')}:{db_config.get('password')}@{db_config.get('host')}/{db_config.get('database')}"
                db = SQLDatabase.from_uri(db_uri)
                
                self.sql_agent = create_sql_agent(
                    llm=self.model,
                    db=db,
                    agent_type="tool-calling",
                    verbose=True
                )
            except ImportError:
                print("Missing required packages for SQL Agent. Try: pip install langchain-community SQLAlchemy mysql-connector-python")
            except Exception as e:
                print(f"Failed to initialize SQL Agent: {e}")

    def ask(self, query: str, chat_history: list):
        """Handles conversational queries by maintaining context from the chat history."""
        # Check if we have the SQL agent and should route to it
        if self.sql_agent:
            # Semantic routing: Let the LLM decide if this requires querying the database
            router_prompt = ChatPromptTemplate.from_messages([
                ("system", "Does this user query require fetching specific records (e.g., students, teachers, grades, attendance) from a school database? Respond strictly with 'YES' or 'NO'."),
                ("user", "{query}")
            ])
            decision = (router_prompt | self.model | StrOutputParser()).invoke({"query": query}).strip().upper()
            
            if "YES" in decision:
                try:
                    agent_query = query if self.is_admin else f"{query} (Please only provide non-sensitive public school data)"
                    response = self.sql_agent.invoke({"input": agent_query})
                    return response.get("output", "I couldn't find an answer to that.")
                except Exception as e:
                    print(f"SQL Agent error: {e}, falling back to standard chat.")

        history = []
        for msg in chat_history[:-1]:
            # Map Streamlit role names to LangChain message classes
            role_class = HumanMessage if msg["role"] == "user" else AIMessage
            history.append(role_class(content=msg["content"]))

        return self.chain.invoke({
            "input": query,
            "history": history
        })

    def extract_entities(self, query: str) -> SearchParams:
        """Uses Gemini to extract names and subjects from a natural language query."""
        system_prompt = (
            "You are a linguistic parser for a school system. "
            "Extract names and subjects from the user's request. "
            "If a name is provided, capitalize it correctly."
        )
        return self.extractor_model.invoke([("system", system_prompt), ("user", query)])

    def analyze_image(self, image_bytes: bytes) -> str:
        """Uses Gemini's Vision capabilities to analyze an uploaded image."""
        import base64
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        
        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Please analyze this image and provide a summary of its contents. If it is a document or report card, extract and summarize the key information clearly."
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}
                }
            ]
        )
        
        try:
            response = self.model.invoke([message])
            return response.content
        except Exception as e:
            return f"Error analyzing image: {e}"