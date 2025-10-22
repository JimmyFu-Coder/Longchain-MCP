#!/usr/bin/env python3
# test_pdf_extraction.py - 测试PDF文本提取

import asyncio
from app.services.document_service import document_processor

async def test_pdf_extraction():
    pdf_path = "uploads/feeecb26-ab8d-4038-aaf5-0104d1141363.pdf"

    print(f"🧪 测试PDF文本提取: {pdf_path}")

    try:
        text = await document_processor.extract_text_from_file(pdf_path)

        print(f"提取结果长度: {len(text)}")

        if text.startswith("[Error]"):
            print(f"❌ 提取失败: {text}")
        else:
            print(f"✅ 提取成功!")
            print(f"前500字符预览:")
            print(text[:500])
            print("...")

            return text

    except Exception as e:
        print(f"❌ 异常: {e}")
        return None

if __name__ == "__main__":
    asyncio.run(test_pdf_extraction())