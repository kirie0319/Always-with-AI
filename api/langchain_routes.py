import os
import asyncio
from langchain.chains import LLMChain
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import ChatPromptTemplate
from langchain.callbacks.streaming_aiter import AsyncIteratorCallbackHandler
from dotenv import load_dotenv

load_dotenv()
async def stream_tokens(callback):
    async for token in callback.aiter():
        print(token, end="", flush=True)

async def stream_chat():
    print("start chat with langchain you can exit by inputting 'exit'")
    while True:
        user_input = input("\n👤 You: ")
        if user_input.lower() == "exit":
            print("Exiting...")
            break

        callback = AsyncIteratorCallbackHandler()
        llm = ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
            model="anthropic/claude-3.7-sonnet",
            temperature=0.7,
            streaming=True,
            callbacks=[callback]
        )
        memory = ConversationBufferMemory(return_messages=True)
        chain = ConversationChain(llm=llm, memory=memory, verbose=False)

        await asyncio.gather(
            stream_tokens(callback),
            chain.arun(input=user_input)
        )

if __name__ == "__main__":
    asyncio.run(stream_chat())

# prompt_template = PromptTemplate(
#     input_variables=["left_info", "user_input"],
#     template="""
#     You are a helpful assistant that can answer questions and help with tasks.
#     ## information
#     {left_info}
#     ## user input
#     {user_input}
#     """
# )
# chain = LLMChain(llm=llm, prompt=prompt_template)

# async def main():
#     left_info = """
#     # 住宅ローンについて

#     住宅ローンは、銀行からお金を借りて住宅を購入するための金融商品です。通常、返済期間は10〜35年であり、固定金利型と変動金利型があります。
#     """

#     user_input = "summarize this content, and give me the key points"
#     print("\n===== LangChainによる出力 =====\n")
#     result = await chain.arun(left_info=left_info, user_input=user_input)
#     print(result)

# if __name__ == "__main__":
#     asyncio.run(main())