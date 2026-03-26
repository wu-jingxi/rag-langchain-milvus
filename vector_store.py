from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import requests

# 连接 Milvus
connections.connect("default", host="localhost", port="19530")

# 👉 创建集合（只运行一次）
def create_collection():
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=1000)
    ]

    schema = CollectionSchema(fields)
    collection = Collection("rag_collection", schema)

    return collection


# 👉 embedding（你刚刚测通的）
def get_embedding(text):
    res = requests.post(
        "http://localhost:8080/v1/embeddings",
        json={"input": text}
    ).json()

    return res["data"][0]["embedding"]


# 👉 插入数据
def insert_data(texts):
    collection = Collection("rag_collection")

    embeddings = [get_embedding(t) for t in texts]

    data = [
        embeddings,
        texts
    ]

    collection.insert(data)
    collection.flush()

    # 👇👇👇 加这个（关键！！！）
    index_params = {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",
        "params": {"nlist": 128}
    }

    collection.create_index(
        field_name="embedding",
        index_params=index_params
    )

# 👉 检索（核心）
def search(query, top_k=5):
    collection = Collection("rag_collection")
    collection.load()
    query_vec = get_embedding(query)

    results = collection.search(
        data=[query_vec],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["text"]
    )

    docs = [hit.entity.get("text") for hit in results[0]]

    return docs