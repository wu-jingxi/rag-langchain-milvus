import json
from pymilvus import connections, Collection
from vector_store import create_collection, insert_data

# 1. 连接并清理旧数据
connections.connect("default", host="localhost", port="19530")

try:
    # 必须删除旧集合，因为表结构（Schema）变了，不删会报错
    old_col = Collection("rag_collection")
    old_col.drop()
    print("🗑️ 旧集合已删除，准备应用新表结构")
except:
    print("💡 集合不存在，准备创建新集合")

# 2. 重新创建集合（应用你刚改好的 6 个字段结构）
create_collection()

# 3. 读取你的 JSON 文件
json_file_path = "debug_chunks.json" # 确保文件名正确

try:
    with open(json_file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # --- 核心：拆解 JSON 数据 ---
    # 我们要把 JSON 里的数据分门别类装进 5 个对应的“篮子”里
    texts = []
    types = []
    sections = []
    sources = []
    importances = []

    for item in raw_data:
        # 提取正文
        texts.append(item.get("content", ""))
        
        # 提取 metadata 里的各个字段
        meta = item.get("metadata", {})
        types.append(meta.get("type", "none"))
        sections.append(meta.get("section", "unknown"))
        sources.append(meta.get("source", "unknown"))
        importances.append(meta.get("importance", "low"))

    print(f"📂 成功读取 {len(texts)} 条数据，准备录入...")

    # 4. 调用新版 insert_data
    # 这里的参数顺序必须和你 vector_store.py 里定义的一致
    insert_data(texts, types, sections, sources, importances)
    
    print("✅ 数据及元数据已全部重新录入 Milvus！")

except FileNotFoundError:
    print(f"❌ 找不到 JSON 文件，请检查路径：{json_file_path}")
except Exception as e:
    print(f"❌ 录入过程中发生错误: {e}")