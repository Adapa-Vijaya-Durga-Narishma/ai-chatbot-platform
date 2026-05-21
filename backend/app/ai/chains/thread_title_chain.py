"""
LangChain LCEL chain for generating chat thread titles.
Format: prompt | llm | parser
"""
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm import llm

prompt_path = Path(__file__).parent.parent / "prompts" / "thread_title_prompt.txt"
with open(prompt_path, encoding="utf-8") as f:
    prompt_text = f.read()

prompt = PromptTemplate(template=prompt_text, input_variables=["message"])
thread_title_chain = prompt | llm | StrOutputParser()


async def generate_thread_title(message: str, user_email: str) -> str:
    title = await thread_title_chain.ainvoke(
        {"message": message},
        config={"metadata": {"user_email": user_email}},
    )
    cleaned = " ".join(title.strip().split())
    return cleaned[:255]
