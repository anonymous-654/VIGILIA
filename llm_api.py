import os
import re
from typing import List

from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI
from together import Together

load_dotenv()

azure_openai_endpoint = os.getenv("AZUREOPENAI_ENDPOINT")  
deployment = "gpt-4o-mini"
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
together_api_key = os.getenv("TOGETHER_API_KEY")
api_version = "2024-12-01-preview"


gpt_client = AzureOpenAI(
  azure_endpoint = azure_openai_endpoint,
  api_key=azure_openai_key,
  api_version=api_version,
)

together_client = Together(api_key=together_api_key)

# client = OpenAI(api_key=openai_api_key)

NODE_HOSTNAME = "gl1516.arc-ts.umich.edu" 

local_client = OpenAI(
    base_url=f"http://{NODE_HOSTNAME}:8001/v1",
    api_key="EMPTY"
)


small_client = OpenAI(
    base_url="http://gl1516.arc-ts.umich.edu:8001/v1",
    api_key="EMPTY"
)


def extract_response_from_local_llm(text: str) -> str:
    """
    Removes <think>...</think> blocks and returns only the final model response.
    """
    # Remove the think block (including multiline content)
    if text is None:
        raise ValueError("extract_response_from_local_llm got None")
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return cleaned.strip()


def query_llm(model_path:str, sys_prompt: str = None, user_prompt: str = "", temperature=0):

  if "gpt" in model_path:
    client = gpt_client
  else:
    client = local_client
  messages = []
  if sys_prompt is not None:
    messages.append({"role": "system", "content": sys_prompt})
  if user_prompt is not None:
    messages.append({"role": "user", "content": user_prompt})
  response = client.chat.completions.create(
      # model="gpt-4o-mini", # "gpt-4-32k", # model = "deployment_name".
      # model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
      # model="gpt-4.1-mini",
      model=model_path,
      messages=messages,
      seed=42,
      extra_body={
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": False},}, 
  )
  
  res = response.choices[0].message.content
  if "Qwen" in model_path: 
    res = extract_response_from_local_llm(res)
  return res, response.usage.prompt_tokens, response.usage.completion_tokens

def query_small_llm(
    sys_prompt: str = None,
    user_prompt: str = "",
    temperature=0
):
    client = small_client
    messages = []

    if sys_prompt is not None:
        messages.append({"role": "system", "content": sys_prompt})
    if user_prompt is not None:
        messages.append({"role": "user", "content": user_prompt})

    response = client.chat.completions.create(
        model="Qwen/Qwen3.5-27B-FP8",
        messages=messages,
        seed=42,
        temperature=0.7,
        extra_body={
                "top_k": 20,
                "chat_template_kwargs": {"enable_thinking": False},}, 
    )

    res = response.choices[0].message.content

    # if "Qwen" in model_path:
    res = extract_response_from_local_llm(res)

    return res, response.usage.prompt_tokens, response.usage.completion_tokens

# def query_small_llm(model_path:str, sys_prompt: str = None, user_prompt: str = "", temperature=0):
#   client = small_client
#   messages = []
#   if sys_prompt is not None:
#     messages.append({"role": "system", "content": sys_prompt})
#   if user_prompt is not None:
#     messages.append({"role": "user", "content": user_prompt})
#   response = client.chat.completions.create(
#       model="Qwen/Qwen3.5-27B-FP8",
#       messages=messages,
#       seed=42,
#   )
  
#   res = response.choices[0].message.content
#   if "Qwen" in model_path: 
#     res = extract_response_from_local_llm(res)
#   return res, response.usage.prompt_tokens, response.usage.completion_tokens




# def query_small_llm(sys_prompt: str = None, user_prompt: str = "", temperature=0):

#   messages = []
#   if sys_prompt is not None:
#     messages.append({"role": "system", "content": sys_prompt})
#   if user_prompt is not None:
#     messages.append({"role": "user", "content": user_prompt})
#   response = gpt_client.chat.completions.create(
#       model="gpt-4o-mini", # "gpt-4-32k", # model = "deployment_name".
#       messages=messages,
#       temperature=temperature,
#       seed=42,
#   )
#   return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens


# def query_local_llm(sys_prompt: str = None, user_prompt: str = None):

#   messages = []
#   if sys_prompt is not None:
#     messages.append({"role": "system", "content": sys_prompt})
#   if user_prompt is not None:
#     messages.append({"role": "user", "content": user_prompt})
#   response = local_client.chat.completions.create(
#       model="Qwen/Qwen3-32B", # "gpt-4-32k", # model = "deployment_name".
#       messages=messages,
#        max_tokens=2048,
#       seed=42,
#   )
#   return response.choices[0].message.content, response.usage.prompt_tokens, response.usage.completion_tokens