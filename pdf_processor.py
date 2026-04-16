import pdfplumber
import re
import json


def get_clean_iso_text_and_tables(pdf_path):
    """
    输出：
    1. clean text（用于你原来的chunk）
    2. tables（保存为json）
    """
    final_text_list = []
    all_tables = []
    
    print(f"正在读取文件: {pdf_path}")
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx, page in enumerate(pdf.pages):

            # ========================
            # ✅ 1. 先提取文本（更安全）
            # ========================
            page_text = page.extract_text()

            # ========================
            # ✅ 2. 再提取表格（新增🔥）
            # ========================
            tables = page.extract_tables()
            for table in tables:
                if table:
                    # ⭐ 清洗表格（新增）
                    clean_table = []
                    for row in table:
                        clean_row = []
                        for cell in row:
                            if cell:
                                cell = cell.replace("\n", "").strip()
                            clean_row.append(cell)
                        clean_table.append(clean_row)

                    all_tables.append({
                        "page": page_idx + 1,
                        "table": clean_table
                    })

            # ========================
            # ✅ 3. 原有文本逻辑（完全不动）
            # ========================
            if not page_text:
                continue
            
            lines = page_text.split('\n')
            clean_lines = []
            
            for line in lines:
                line_strip = line.strip()
                
                if line_strip.isdigit() or re.match(r'^—?\s*\d+\s*—?$', line_strip):
                    continue
                
                if "ISO 14067" in line_strip and len(line_strip) < 40:
                    continue
                
                clean_lines.append(line)
            
            final_text_list.append("\n".join(clean_lines))

    # ========================
    # 文本处理（原逻辑）
    # ========================
    full_content = "\n".join(final_text_list)

    last_index = full_content.rfind("1.范围")
    if last_index == -1:
        last_index = full_content.rfind("1 范围")
    
    if last_index != -1:
        print("已定位正文起点，成功切除目录部分。")
        full_content = full_content[last_index:]
    else:
        print("警告：未能识别到正文起始标志，将保留全文。")

    full_content = re.sub(r'(\n\d+\.\d+)([^\s\d\.])', r'\1 \2', full_content)
    full_content = re.sub(r'\n\s*(\d+\.\d+)', r'\n\1', full_content)

    return full_content, all_tables

def merge_tables(tables):
    merged_tables = []

    current_table = None

    for t in tables:
        table = t["table"]

        # 判断是不是新表（有“子条款”）
        first_row = table[0]

        is_new_table = any(cell and "子条款" in cell for cell in first_row)

        if is_new_table:
            # 开新表
            if current_table:
                merged_tables.append(current_table)

            current_table = {
                "page": t["page"],
                "table": table
            }

        else:
            # 👉 续表（关键🔥）
            if current_table:
                current_table["table"].extend(table)
            else:
                # 极端情况：没有表头直接出现
                current_table = t

    if current_table:
        merged_tables.append(current_table)

    return merged_tables

def merge_rows_by_clause(tables):
    final_rows = []

    for t in tables:
        table = t["table"]

        header1 = table[0]
        header2 = table[1]

        merged_headers = []
        for h1, h2 in zip(header1, header2):
            h1 = (h1 or "").strip()
            h2 = (h2 or "").strip()

            if h1 and h2:
                merged_headers.append(h1 + "_" + h2)
            elif h1:
                merged_headers.append(h1)
            else:
                merged_headers.append(h2)

        # ⭐ 关键：不再按 clause merge
        for row in table[2:]:
            row = [(cell or "").strip() for cell in row]

            clause = row[0]

            if not clause or clause.startswith("a."):
                continue

            row_dict = dict(zip(merged_headers, row))

            final_rows.append(row_dict)

    return final_rows

def clean_text(text):
    # 去掉脚注 a b c
    return re.sub(r'[a-zA-Z]$', '', text).strip()


def convert_tables_to_rag_chunks(tables):
    rag_chunks = []

    for row in tables:
        clause = row.get("子条款", "").strip()
        values = list(row.values())

        if len(values) < 2:
            continue

        desc = clean_text(values[1])

        if not clause or not desc:
            continue

        content = f"【约束】{desc}（{clause}）\n\n要求：\n"

        rules = []

        # ===== 核心语义映射（关键🔥） =====

        if row.get("产品碳足迹的处理_必须包括") == "x":
            rules.append("必须纳入产品碳足迹计算")

        if row.get("应该包括") == "x":
            rules.append("建议纳入产品碳足迹计算")

        if row.get("应考虑") == "x":
            rules.append("应考虑纳入产品碳足迹计算")

        if row.get("在产品碳足迹报告中的记录_必须记录") == "x":
            rules.append("必须在碳足迹报告中记录")

        if row.get("如果计算，应记录") == "x":
            rules.append("若进行计算，应在报告中说明")

        # 没规则就跳过
        if not rules:
            continue

        # 拼接
        for r in rules:
            content += f"- {r}\n"

        rag_chunks.append({
            "content": content.strip(),
            "metadata": {
                "type": "constraint",
                "section": clause,
                "source": "ISO 14067",
                "importance": "high"
            }
        })

    return rag_chunks
# --- 测试运行 ---
if __name__ == "__main__":
    pdf_file = r"C:\Users\lenovo\Downloads\ISO14067.pdf"
    
    try:
        text, tables = get_clean_iso_text_and_tables(pdf_file)
        tables = merge_tables(tables)
        tables = merge_rows_by_clause(tables)
        rag_chunks = convert_tables_to_rag_chunks(tables)
        # ========================
        # ✅ 保存文本（完全不变）
        # ========================
        with open("raw_material_check.txt", "w", encoding="utf-8") as f:
            f.write(text)
        with open("rag_table_chunks.json", "w", encoding="utf-8") as f:
            json.dump(rag_chunks, f, ensure_ascii=False, indent=2)

        print(f"✅ RAG表格chunk已生成，共 {len(rag_chunks)} 条")

        print("✅ 文本已保存：raw_material_check.txt")

        # ========================
        # ✅ 保存表格（优化后）
        # ========================
        with open("tables.json", "w", encoding="utf-8") as f:
            json.dump(tables, f, ensure_ascii=False, indent=2)

        print(f"✅ 表格已保存：tables.json，共 {len(tables)} 个表格")

    except Exception as e:
        print(f"❌ 处理失败，原因: {e}")