"""
LangChain LCEL RAG chain.
Format: prompt | llm | parser
"""
from pathlib import Path

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from app.ai.llm import llm

prompt_path = Path(__file__).parent.parent / "prompts" / "rag_prompt.txt"
with open(prompt_path, encoding="utf-8") as f:
    prompt_text = f.read()

prompt = PromptTemplate(
    template=prompt_text,
    input_variables=["context", "history", "human_input"],
)

rag_chain = prompt | llm | StrOutputParser()
