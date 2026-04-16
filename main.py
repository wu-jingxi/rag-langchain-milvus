import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
# 导入你之前的组件
from retriever import retrieve
from reranker import rerank

# --- 1. 配置 Qwen API ---
DASHSCOPE_API_KEY = "sk-648d3fd76f2e464d9b037c82d17df2dc" 

llm = ChatOpenAI(
    model="qwen-plus", 
    openai_api_key=DASHSCOPE_API_KEY,
    openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    temperature=0.1
)

# --- 2. 包装原有的检索和重排组件 ---
retriever_chain = RunnableLambda(retrieve).with_config(
    {"run_name": "Milvus向量检索"}
)

reranker_chain = RunnableLambda(
    lambda x: rerank(x["query"], x["docs"])
).with_config({"run_name": "Reranker重排器"})

# --- 3. 定义提示词模板 ---
template = """你是一个专业的 ISO 标准助手。请根据以下提供的【参考资料】来回答用户的问题。

【参考资料】：
{docs}

【用户问题】：
{query}

请结合资料进行专业回答。如果资料中没提到相关内容，请回答“知识库中未找到相关具体规定”。

回答内容："""

prompt = ChatPromptTemplate.from_template(template)

# --- 4. 组装最终的 RAG 链 (LCEL 语法) ---
# 流程：输入字符串 -> 检索 -> 重排 -> 提示词 -> 大模型 -> 解析文字
full_rag_chain = (
    # A. 准备数据：检索并重排
    RunnableLambda(lambda x: {"query": x}) 
    .assign(docs=lambda x: retriever_chain.invoke(x["query"]))
    | {
        "docs": reranker_chain | (lambda x: "\n\n".join(x[:3])), # 取前3条并合并
        "query": lambda x: x["query"]
    }
    # B. 生成答案
    | prompt 
    | llm 
    | StrOutputParser()
).with_config({"run_name": "ISO-RAG全流程"})

# --- 5. 运行 ---
if __name__ == "__main__":
    # 检查 LangSmith 监控（可选）
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("💡 提示：未检测到 LangSmith API KEY，本次运行将不会记录 Trace。")

    print("🚀 ISO 标准智能助手已就绪")
    
    while True:
        query_text = input("\n👤 请输入您的问题 (输入 exit 退出): ")
        if query_text.lower() in ['exit', 'quit']:
            break
            
        print("🔍 正在检索并思考...")
        try:
            # 运行完整链条
            answer = full_rag_chain.invoke(query_text)
            print(f"\n🤖 AI 回答：\n{answer}")
        except Exception as e:
            print(f"❌ 出错了: {e}")