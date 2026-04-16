from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import requests

# 连接 Milvus
connections.connect("default", host="localhost", port="19530")

# 👉 1. 创建集合（增加了元数据字段）
def create_collection():
    fields = [
        # 主键 ID
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        # 向量坐标 (1024维)
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
        # 原始正文
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4000),
        # --- 新增元数据字段 ---
        FieldSchema(name="type", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="section", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=100),
        FieldSchema(name="importance", dtype=DataType.VARCHAR, max_length=50)
    ]

    schema = CollectionSchema(fields, description="带元数据的RAG知识库")
    collection = Collection("rag_collection", schema)
    return collection

# 👉 2. Embedding（保持不变）
def get_embedding(text):
    res = requests.post(
        "http://localhost:8080/v1/embeddings",
        json={"input": text}
    ).json()
    return res["data"][0]["embedding"]

# 👉 3. 插入数据（现在接收正文和元数据列表）
def insert_data(texts, types, sections, sources, importances):
    collection = Collection("rag_collection")

    # 把文字变成向量
    embeddings = [get_embedding(t) for t in texts]

    # 按照 Schema 定义的顺序组织数据包
    # 注意：数据顺序必须和 create_collection 里的定义顺序一致（除了 auto_id 的列）
    data = [
        embeddings,     # 对应 embedding
        texts,          # 对应 text
        types,          # 对应 type
        sections,       # 对应 section
        sources,        # 对应 source
        importances     # 对应 importance
    ]

    collection.insert(data)
    collection.flush()

    # 建立索引
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",
        "params": {"nlist": 128}
    }
    collection.create_index(field_name="embedding", index_params=index_params)

# 👉 4. 检索（现在可以输出更多字段了）
def search(query, top_k=5):
    collection = Collection("rag_collection")
    collection.load()
    query_vec = get_embedding(query)

    results = collection.search(
        data=[query_vec],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["text", "section", "source"] # 这里可以要求返回元数据
    )

    # 提取结果：我们把正文和来源拼接一下，方便阅读
    docs = []
    for hit in results[0]:
        text = hit.entity.get("text")
        source = hit.entity.get("source")
        section = hit.entity.get("section")
        docs.append(f"【来源：{source} 章节：{section}】\n{text}")

    return docs