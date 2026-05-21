"""
LangChain LCEL chat chain.
Format: prompt | llm (no LLMChain, SequentialChain, or ConversationalRetrievalChain)
Prompt is loaded from file, not hardcoded.
"""
from pathlib import Path

from langchain_core.prompts import PromptTemplate

from app.ai.llm import llm

# ── Load prompt from file ────────────────────────────────────────────────────
prompt_path = Path(__file__).parent.parent / "prompts" / "chat_prompt.txt"
with open(prompt_path) as f:
    prompt_text = f.read()

prompt = PromptTemplate(
    template=prompt_text,
    input_variables=["history", "human_input", "attachment_context"],
)

# ── Build chain: prompt | llm ───────────────────────────────────────────────
chat_chain = prompt | llm
