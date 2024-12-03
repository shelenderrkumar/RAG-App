from typing import Any, Literal, TypedDict, cast, Dict, Optional
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.documents import Document

from .configuration import AgentConfiguration
from ..shared.utils import format_docs, load_chat_model, send_email
from ..shared import retrieval
from .state import AgentState, InputState

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

async def retrieve_documents(
    query: str, *, config: RunnableConfig
) -> dict[str, list[Document]]:
    """Retrieve documents based on a given query.

    This function uses a retriever to fetch relevant documents for a given query.

    Args:
        state (QueryState): The current state containing the query string.
        config (RunnableConfig): Configuration with the retriever used to fetch documents.

    Returns:
        dict[str, list[Document]]: A dictionary with a 'documents' key containing the list of retrieved documents.
    """
    with retrieval.make_retriever(config) as retriever:
        response = await retriever.ainvoke(query, config)
        return {"documents": response}
    

async def initial_overview(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Generate initial company overview."""
    
    messages = state.messages
    print("inside initial")
    
    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=False)
    docs = await retrieve_documents("product overview", config=config)
    
    overview_prompt = f"""
    Start by greeting the user and providing a brief overview of the company.
    Provide a concise 2-sentence overview of our product information enclosed in triple backticks. Focus on being engaging and informative. \
    The information about product is; ```{docs}```

    After prvoding the overview, ask the user if they would like to learn more about the product in detail.
    """
    messages = messages + [SystemMessage(content=overview_prompt)]
        
    response = await model.ainvoke(messages, config)
    
    return {
        "messages": [response],
        "router": {"type": "initial", "logic": "ask_user_interest"} 
    }


async def ask_user_interest(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Ask if user wants more company information."""
   
    pass


async def check_user_interest(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Checks user interest in more company details."""

    class UserInterest(BaseModel):
        """Binary score for interest check."""
        more_company_details: str = Field(description="User's interest in detailed product info 'yes' or 'no'")

    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=True)
    model_with_tool = model.with_structured_output(UserInterest)
    llm_with_tool = model_with_tool.with_config(tags=["nostream"])

    # Prompt
    prompt = PromptTemplate(
        template="""You are a virtual assistant helping a user learn more about a product. 
        The user has been provided with an initial overview of the product. 
        Now, you need to determine if the user is interested in more detailed information about the company.
        Here is the user's response: {user_response}
        Based on this response, indicate if the user wants more detailed information about the company with a 'yes' or 'no'.""",
        input_variables=["user_response"],
    )

    chain = prompt | llm_with_tool

    user_response = state.user_feedback

    scored_result = chain.invoke({"user_response": user_response})

    score = scored_result.more_company_details

    if score == "yes":
        return {
            "messages": [AIMessage(content="Great! I will provide you with more detailed information about our company.")],
            "router": {"type": "more_details", "logic": "conduct_research"}
        }
    else:
        return {
            "messages": [AIMessage(content="No problem! If you have any other questions or need further assistance, feel free to ask.")],
            "router": {"type": "overview", "logic": "conversation_complete"}
        }


async def conduct_research(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Any]:
    """Conduct research based on user's interest."""
    
    messages = state.messages
    
    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=False)

    docs = await retrieve_documents("Provide comprehensive details about the product", config=config)
    prompt = f"""
    Give a response to the user provinding more detailed information about the company \
    Provide the company details directly without starting with words like 'sure' or 'okay.
    Detailed overview of our product:
    ```{docs}```

    After providing the detailed overview, ALWAYS ask the user if they would like to receive a comprehensive company profile via email.
    """
    messages = messages + [SystemMessage(content=prompt)]
        
    response = await model.ainvoke(messages, config)
    
    return {
        "messages": [response],
    }



async def ask_email_interest(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage]]:
    """Ask if user wants to recieve company profile via email."""
   
    pass


async def check_email_profile_interest(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, list[BaseMessage] | dict]:
    """Checks user interest in more company details."""

    class UserInterest(BaseModel):
        """Binary score for email profile interest check."""
        recieve_email: str = Field(description="User's interest in recieving product profile via email 'yes' or 'no'")

    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=True)
    model_with_tool = model.with_structured_output(UserInterest)
    llm_with_tool = model_with_tool.with_config(tags=["nostream"])

    # Prompt
    prompt = PromptTemplate(
    template="""You are a virtual assistant helping a user provide their email address.
    The user was asked to provide their email address to receive the company profile.
    Extract the email address from the user's response.

    If the user's response includes phrases like "I don't have email", "No email", "Not applicable", or any other indication that they do not want to provide an email, output 'None'.
    Otherwise, extract the email address and return it.

    User's response: {user_response}

    IF THE USER DID NOT PROVIDE AN EMAIL ADDRESS or IF IT DID NOT MATCH A COMMON EMAIL FORMAT, OUTPUT 'None'.""",
    input_variables=["user_response"],
)

    chain = prompt | llm_with_tool

    user_response = state.user_feedback

    scored_result = chain.invoke({"user_response": user_response})

    score = scored_result.recieve_email

    if score == "yes":
        return {
            "messages": [AIMessage(content="Great! I will send you company profile via email. Can you provide your email address?")],
            "router": {"type": "email_request", "logic": "get_email"}
        }
    else:
        return {
            "messages": [AIMessage(content="No problem! If you have any other questions or need further assistance, feel free to ask.")],
            "router": {"type": "overview", "logic": "conversation_complete"}
        }



async def collect_email(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Any]:
    """Collect user's email address."""
    pass


async def validate_email(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Any]:
    """Validate and collect user email."""

    class EmailExtraction(BaseModel):
        """Model to extract email address from user's message."""
        email_address: str = Field(description="The user's email address or None")


    model = ChatOpenAI(temperature=0, model="gpt-4o-mini", streaming=False)
    model_with_tool = model.with_structured_output(EmailExtraction)
    llm_with_tool = model_with_tool.with_config(tags=["nostream"])

    # Prompt
    prompt = PromptTemplate(
            template="""You are a virtual assistant helping a user provide their email address.
            The user was asked to provide their email address to receive the company profile.
            Extract the email address from the user's response.

            User's response: {user_response}

            IF THE USER DID NOT PROVIDE AN EMAIL ADDRESS or IR DID NOT MATCH COMMON EMAIL FORMAT, OUTPUT 'None'.""",
            input_variables=["user_response"],
    )

    chain = prompt | llm_with_tool

    user_response = state.user_feedback

    extracted_result = chain.invoke({"user_response": user_response})

    email_address = extracted_result.email_address
    print(f"\n\nExtracted email address: {email_address}\n\n")

    if email_address.lower() != "none":
        state.email = email_address
        return {
            "messages": [AIMessage(content=f"Perfect! Your email address is: {state.email}. I will send the company profile to this email address.")],
            "router": {"type": "send_company_profile", "logic": "email_validated"}
        }
    else:
        return {
            "messages": [AIMessage(content="I couldn't find an email address in your message. Could you please provide it?")],
            "router": {"type": "collect_email", "logic": "get_email"}
        }




async def send_company_profile(
    state: AgentState, *, config: RunnableConfig
) -> dict[str, Any]:
    """Send company profile via email."""
    send_email(state.email, format_docs(state.documents))
    
    return {
        "messages": [
            AIMessage(content=f"Company profile has been sent to {state.email}. Is there anything else I can help you with?")
        ],
        "email": {"email_sent": True},
        "router": {"type": "overview", "logic": "conversation_complete"}
    }



builder = StateGraph(AgentState, input=InputState, config_schema=AgentConfiguration)
builder.add_node("initial_overview", initial_overview)
builder.add_node("ask_user_interest", ask_user_interest)
builder.add_node("check_user_interest", check_user_interest)
builder.add_node("conduct_research", conduct_research)
builder.add_node("ask_email_interest", ask_email_interest)
builder.add_node("check_email_profile_interest", check_email_profile_interest)
builder.add_node("collect_email", collect_email)
builder.add_node("validate_email", validate_email)
builder.add_node("send_company_profile", send_company_profile)


builder.add_edge(START, "initial_overview")
builder.add_conditional_edges(
    "initial_overview",
    lambda state: state.router['type'],
    {
        "initial": "ask_user_interest"
    }
)
builder.add_edge("ask_user_interest", "check_user_interest")
builder.add_conditional_edges(
    "check_user_interest", 
    lambda state: state.router['type'],
    {
        "more_details": "conduct_research",
        "overview": END
    }
)

builder.add_edge("conduct_research", "ask_email_interest")
builder.add_edge("ask_email_interest", "check_email_profile_interest")
builder.add_conditional_edges(
    "check_email_profile_interest", 
    lambda state: state.router['type'],
    {
        "email_request": "collect_email",
        "overview": END
    }
)
builder.add_edge("collect_email", "validate_email")

builder.add_edge("validate_email", "send_company_profile")
builder.add_edge("send_company_profile", END)

memory = MemorySaver()


app = builder.compile(
    checkpointer=memory, 
    interrupt_before=[
        "ask_user_interest", 
        "ask_email_interest",
        "collect_email"
    ]
)
app.name = "CompanyProfileRetrievalGraph"