import re
import json

class ISOProcessor:
    def __init__(self):
        pass

    def split_rule(self, text_segment, current_chapter):
        chunks = []

        # ✅ 统一换行符（关键）
        text_segment = text_segment.replace('\r\n', '\n')
        chapter_start = re.search(rf"(?:^|\n){current_chapter}\.", text_segment)

        chapter_end = re.search(
            rf"\n{int(current_chapter)+1}(?:\.|\s)",
            text_segment
        )

        if chapter_start:
            start_idx = chapter_start.start()
            end_idx = chapter_end.start() if chapter_end else len(text_segment)
        text_segment = text_segment[start_idx:end_idx]
        # ✅ 支持无空格标题（核心修复）
        pattern = rf"(?:^|\n)({current_chapter}\.\d+(?:\.\d+)*)"

        all_matches = list(re.finditer(pattern, text_segment))

        print(f"👉 共检测到 {len(all_matches)} 个候选标题")

        valid_matches = []
        last_section_numbers = [int(current_chapter), 0]

        for m in all_matches:
            section_id = m.group(1)
            current_numbers = [int(x) for x in section_id.split('.')]

            # 获取当前行内容
            start = m.end()
            end_line = text_segment.find('\n', start)
            if end_line == -1:
                end_line = len(text_segment)

            line_content = text_segment[start:end_line].strip()

            is_real_header = False

            if current_numbers > last_section_numbers:
                if not re.search(r'[。；）\);]', line_content):
                    is_real_header = True

            if is_real_header:
                print(f"✅ 识别标题: {section_id} -> {line_content[:20]}")
                valid_matches.append(m)
                last_section_numbers = current_numbers
            else:
                print(f"❌ 拦截: {section_id} -> {line_content[:20]}")

        print(f"\n👉 有效标题数量: {len(valid_matches)}\n")

        # 切分
        for i, m in enumerate(valid_matches):
            section_id = m.group(1)

            start_pos = m.end()
            # 找下一个同级或更高章节（例如 8.x）
            next_boundary = re.search(
            rf"\n{int(current_chapter)+1}(?=[\.\s\u4e00-\u9fa5])",
            text_segment[start_pos:]
            )

            if i+1 < len(valid_matches):
                end_pos = valid_matches[i+1].start()
            elif next_boundary:
                end_pos = start_pos + next_boundary.start()
            else:
                end_pos = len(text_segment)

            raw_segment = text_segment[start_pos:end_pos].strip()

            lines = raw_segment.split('\n', 1)
            title = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""

            def get_importance_by_chapter(section_id):
                if section_id.startswith("6"):
                    return "high"       # 核心量化规则
                elif section_id.startswith("5"):
                    return "medium"     # 原则
                elif section_id.startswith("7"):
                    return "medium"     # 报告
                elif section_id.startswith("3"):
                    return "low"        # 术语定义
                else:
                    return "low"


            chunks.append({
                "content": f"【量化要求】{title} (章节：{section_id})\n内容：{body}",
                "metadata": {
                    "type": "rule",                  # ✅ 固定
                    "section": section_id,
                    "source": "ISO 14067",           # ✅ 固定
                    "importance": get_importance_by_chapter(section_id)
                }
            })

        return chunks


# ✅ ====== 运行入口（关键，你刚刚缺的就是这个）======
if __name__ == "__main__":
    processor = ISOProcessor()

    file_path = "raw_material_check.txt"

    try:
        print(f"📂 正在读取文件: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            test_data = f.read()

        print(f"📄 文件长度: {len(test_data)} 字符\n")

        # ✅ 想处理哪些章节，在这里写
        chapters_to_process = ["3", "5", "6", "7"]

        result_chunks = []

        for ch in chapters_to_process:
            print(f"\n🚀 正在处理第 {ch} 章")
            chunks = processor.split_rule(test_data, ch)
            result_chunks.extend(chunks)

        print(f"\n✅ 最终切分得到 {len(result_chunks)} 个 chunk\n")

        # 打印前几个
        for chunk in result_chunks[:5]:
            print(f"ID: {chunk['metadata']['section']}")
            print(f"TEXT: {chunk['content'][:80]}...")
            print("-" * 40)

        # 保存 JSON
        with open("debug_chunks.json", "w", encoding="utf-8") as f:
            json.dump(result_chunks, f, ensure_ascii=False, indent=4)

        print("\n💾 已保存到 debug_chunks.json")

    except FileNotFoundError:
        print(f"❌ 错误：没找到文件 {file_path}")
    except Exception as e:
        print(f"❌ 读取或处理出错: {e}")