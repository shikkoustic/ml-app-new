from langchain.agents import initialize_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_agent.tools import get_aqi_forecast

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key="",
    temperature=0.3
)

tools = [get_aqi_forecast]

agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True,
    max_iterations=2,
    early_stopping_method="generate",
    handle_parsing_errors=True
)