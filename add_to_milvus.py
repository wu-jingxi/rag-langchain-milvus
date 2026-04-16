import json

with open("debug_chunks.json", "r", encoding="utf-8") as f:
    text_chunks = json.load(f)

with open("rag_table_chunks.json", "r", encoding="utf-8") as f:
    table_chunks = json.load(f)

all_chunks = text_chunks + table_chunks

with open("all_chunks.json", "w", encoding="utf-8") as f:
    json.dump(all_chunks, f, ensure_ascii=False, indent=2)

print(f"✅ 总chunk数: {len(all_chunks)}")