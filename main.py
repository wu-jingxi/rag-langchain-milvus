import os
from retriever import retrieve
from reranker import rerank
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

# --- 1. 定义 LangChain 组件 ---

# 包装检索器：它接收 query(str)，输出 docs(list)
retriever_chain = RunnableLambda(retrieve).with_config(
    {"run_name": "Milvus向量检索"}
)

# 包装重排器：它接收一个 dict {"query": ..., "docs": ...}，输出过滤后的 list
reranker_chain = RunnableLambda(
    lambda x: rerank(x["query"], x["docs"])
).with_config({"run_name": "Reranker重排器"})

# --- 2. 组装 LCEL 链 (这是看到中间过程的关键) ---

# 这里的逻辑是：
# 1. RunnablePassthrough() 拿到原始 query
# 2. .assign(docs=...) 调用检索器，并将结果存入 docs 键
# 3. 此时数据流变成 {"query": "熊猫...", "docs": ["文档1", "文档2"...]}
# 4. 整体传给 reranker_chain 进行重排
# 5. 最后截取前 2 条
full_chain = (
    # 第一步：把输入的字符串 "熊猫是什么" 包装成字典 {"query": "熊猫是什么"}
    RunnableLambda(lambda x: {"query": x}) 
    # 第二步：现在输入是字典了，可以用 .assign 增加 docs 字段
    .assign(docs=lambda x: retriever_chain.invoke(x["query"]))
    # 第三步：传给重排器
    | reranker_chain
    # 第四步：切片取前两个
    | (lambda x: x[:2])
).with_config({"run_name": "RAG全流程监控"})
# --- 3. 运行 ---

if __name__ == "__main__":
    # 验证环境变量是否读取成功（PowerShell 设置的变量通常只在当前窗口有效）
    if not os.environ.get("LANGCHAIN_API_KEY"):
        print("❌ 未检测到 API KEY，请检查环境变量设置！")
    else:
        query_text = "熊猫是什么"
        print(f"🚀 开始执行查询: {query_text}")
        
        # 运行链
        final_results = full_chain.invoke(query_text)

        print("\n--- 最终 Top 2 结果 ---")
        for i, doc in enumerate(final_results):
            print(f"[{i+1}] {doc}")

        print("\n✨ 检查完成！现在去 LangSmith 网页刷新，你会看到一个带文件夹图标的 Trace。")