"""LangChain Pandas dataframe agent wrapper."""
import logging
from typing import Any

from langchain_classic.agents.agent_types import AgentType
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from pandas import DataFrame

from app.ai.llm import llm

logger = logging.getLogger(__name__)


def get_pandas_agent(dataframe: DataFrame):
    """Create a Pandas DataFrame agent with safe execution enabled."""
    return create_pandas_dataframe_agent(
        llm=llm,
        df=dataframe,
        agent_type=AgentType.OPENAI_FUNCTIONS,
        verbose=True,
        allow_dangerous_code=True,  # Required to use Python REPL for dataframe analysis
        return_intermediate_steps=True,
        max_iterations=6,
    )


def invoke_pandas_agent(dataframe: DataFrame, question: str, user_email: str) -> dict[str, Any]:
    """Invoke the dataframe agent with LiteLLM tracking metadata."""
    logger.info(f"Starting pandas agent invocation for user {user_email}")
    logger.info(f"Dataframe shape: {dataframe.shape}, Question: {question}")
    
    try:
        agent = get_pandas_agent(dataframe)
        logger.info("Agent created successfully")
    except Exception as e:
        logger.exception(f"Failed to create agent: {e}")
        raise
    
    try:
        result = agent.invoke(
            {"input": question},
            config={"metadata": {"user_email": user_email}},
        )
        logger.info(f"Agent invocation successful: {result}")
        return result
    except Exception as e:
        logger.exception(f"Agent invocation failed: {e}")
        raise