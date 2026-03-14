from langchain_google_genai import ChatGoogleGenerativeAI
import os

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key="AIzaSyChVVloFEU1iog7nMd8oS3UjhLytH2KoC4",
    temperature=0.3
)