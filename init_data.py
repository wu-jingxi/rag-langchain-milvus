from pymilvus import connections, Collection

# 1. 连接并清理
connections.connect("default", host="localhost", port="19530")

try:
    # 彻底删除旧集合，确保没有脏数据
    old_col = Collection("rag_collection")
    old_col.drop()
    print("🗑️ 旧集合已删除")
except:
    print("💡 集合不存在，准备创建新集合")

# 2. 重新创建并插入（调用你原来的函数）
from vector_store import create_collection, insert_data

create_collection()

# 确保这组测试数据是唯一的
docs = [
    "熊猫是中国特有的一种动物", # 熊猫 1
    "熊猫喜欢吃竹子",          # 熊猫 2
    "巴黎是法国的首都",        # 地理
    "大象是陆地上最大的动物",   # 动物
    "竹子是熊猫的主要食物"      # 熊猫 3
]

insert_data(docs)
print("✅ 唯一数据已重新录入")