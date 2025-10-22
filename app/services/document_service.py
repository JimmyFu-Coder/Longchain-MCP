# app/services/document_service.py
import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# 文档处理服务
class DocumentProcessor:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def extract_text_from_file(self, file_path: str) -> str:
        """从文件中提取文本内容"""
        file_ext = Path(file_path).suffix.lower()

        if file_ext == '.txt':
            return await self._extract_from_txt(file_path)
        elif file_ext == '.pdf':
            return await self._extract_from_pdf(file_path)
        elif file_ext in ['.docx', '.doc']:
            return await self._extract_from_word(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    async def _extract_from_txt(self, file_path: str) -> str:
        """从TXT文件提取文本"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # 尝试其他编码
            with open(file_path, 'r', encoding='gbk') as f:
                return f.read()

    async def _extract_from_pdf(self, file_path: str) -> str:
        """从PDF文件提取文本"""
        try:
            # 尝试使用PyPDF2提取文本
            import PyPDF2
            text = ""

            with open(file_path, 'rb') as f:
                try:
                    pdf_reader = PyPDF2.PdfReader(f)

                    # 检查PDF是否加密
                    if pdf_reader.is_encrypted:
                        return f"[Error] PDF is encrypted and requires password: {file_path}"

                    total_pages = len(pdf_reader.pages)
                    print(f"处理PDF: {total_pages} 页")

                    for i, page in enumerate(pdf_reader.pages):
                        try:
                            page_text = page.extract_text()
                            if page_text.strip():
                                text += page_text + "\n"
                            else:
                                print(f"第{i+1}页无文本内容（可能是图片页面）")
                        except Exception as page_error:
                            print(f"第{i+1}页提取失败: {page_error}")
                            continue

                    if not text.strip():
                        return f"[Error] No text content found in PDF. This may be a scanned PDF that requires OCR: {file_path}"

                    return text

                except Exception as pdf_error:
                    print(f"PyPDF2处理失败: {pdf_error}")

                    # 尝试使用pdfplumber作为备选方案
                    try:
                        import pdfplumber
                        text = ""
                        with pdfplumber.open(file_path) as pdf:
                            for i, page in enumerate(pdf.pages):
                                try:
                                    page_text = page.extract_text()
                                    if page_text:
                                        text += page_text + "\n"
                                except Exception as page_error:
                                    print(f"pdfplumber第{i+1}页提取失败: {page_error}")
                                    continue

                        if text.strip():
                            print("✅ pdfplumber提取成功")
                            return text
                        else:
                            return f"[Error] No text found with pdfplumber either. PDF may be image-based: {file_path}"

                    except ImportError:
                        return f"[Error] Both PyPDF2 and pdfplumber failed. Consider installing pdfplumber: pip install pdfplumber"
                    except Exception as plumber_error:
                        return f"[Error] Both PyPDF2 and pdfplumber failed. Error: {plumber_error}"

        except ImportError:
            return f"[Error] PyPDF2 not installed. Cannot process PDF file: {file_path}"
        except Exception as e:
            return f"[Error] Failed to extract text from PDF: {str(e)}"

    async def _extract_from_word(self, file_path: str) -> str:
        """从Word文件提取文本"""
        try:
            # 使用python-docx处理.docx文件
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            return f"[Error] python-docx not installed. Cannot process Word file: {file_path}"
        except Exception as e:
            return f"[Error] Failed to extract text from Word document: {str(e)}"

    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """将文本分割成chunks"""
        if not text or text.strip() == "":
            return []

        # 清理文本
        text = self._clean_text(text)

        # 按段落分割
        paragraphs = text.split('\n\n')

        chunks = []
        current_chunk = ""
        current_length = 0
        chunk_index = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            paragraph_length = len(paragraph)

            # 如果当前chunk加上新段落超过限制，保存当前chunk
            if current_length + paragraph_length > self.chunk_size and current_chunk:
                chunks.append({
                    "index": chunk_index,
                    "text": current_chunk.strip(),
                    "length": current_length,
                    "start_char": len(''.join([c["text"] for c in chunks])),
                    "end_char": len(''.join([c["text"] for c in chunks])) + current_length
                })

                # 处理重叠
                if self.chunk_overlap > 0 and current_length > self.chunk_overlap:
                    overlap_text = current_chunk[-self.chunk_overlap:]
                    current_chunk = overlap_text + "\n\n" + paragraph
                    current_length = len(overlap_text) + paragraph_length + 2
                else:
                    current_chunk = paragraph
                    current_length = paragraph_length

                chunk_index += 1
            else:
                # 添加到当前chunk
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                    current_length += paragraph_length + 2
                else:
                    current_chunk = paragraph
                    current_length = paragraph_length

        # 添加最后一个chunk
        if current_chunk.strip():
            chunks.append({
                "index": chunk_index,
                "text": current_chunk.strip(),
                "length": current_length,
                "start_char": len(''.join([c["text"] for c in chunks])),
                "end_char": len(''.join([c["text"] for c in chunks])) + current_length
            })

        return chunks

    def _clean_text(self, text: str) -> str:
        """清理文本，移除多余的空白字符"""
        # 移除多余的空行
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)
        # 移除行尾空白
        text = re.sub(r'[ \t]+\n', '\n', text)
        # 移除多余的空格
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    def calculate_chunk_quality(self, chunk: Dict[str, Any]) -> float:
        """计算chunk质量分数"""
        text = chunk["text"]
        length = chunk["length"]

        score = 0.0

        # 1. 长度分数 (30%)：适中长度获得更高分数
        ideal_length = 600  # 理想长度
        if length < 50:
            length_score = 0.1  # 太短
        elif length > 2000:
            length_score = 0.6  # 太长
        else:
            # 使用高斯函数，在理想长度附近得分最高
            length_score = max(0.1, 1.0 - abs(length - ideal_length) / ideal_length)

        score += length_score * 0.3

        # 2. 信息密度分数 (25%)：标点符号、数字、特殊字符的比例
        total_chars = len(text)
        if total_chars > 0:
            # 计算有效字符比例
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            numbers = len(re.findall(r'[0-9]', text))
            punctuation = len(re.findall(r'[,.!?;:，。！？；：]', text))

            content_chars = chinese_chars + english_chars + numbers
            info_density = content_chars / total_chars if total_chars > 0 else 0

            # 适量的标点符号是好的
            punct_ratio = punctuation / total_chars if total_chars > 0 else 0
            punct_score = 1.0 if 0.02 <= punct_ratio <= 0.15 else max(0.3, 1.0 - abs(punct_ratio - 0.08) * 10)

            density_score = info_density * 0.7 + punct_score * 0.3
        else:
            density_score = 0

        score += density_score * 0.25

        # 3. 结构化程度 (20%)：包含标题、列表、段落结构
        structure_score = 0

        # 检查是否包含标题标识符
        if re.search(r'第[一二三四五六七八九十\d]+[章节条]|Chapter|Section|\d+\.|[一二三四五]、', text):
            structure_score += 0.3

        # 检查是否包含列表结构
        if re.search(r'[1-9]\.|[一二三四五]\.|[①②③④⑤]|•|-\s', text):
            structure_score += 0.3

        # 检查段落结构
        paragraphs = text.split('\n\n')
        if len(paragraphs) >= 2:
            structure_score += 0.2

        # 检查关键词密度
        keywords = ['系统', '功能', '技术', '方法', '应用', '实现', '处理', '管理', '分析']
        keyword_count = sum(1 for word in keywords if word in text)
        if keyword_count >= 2:
            structure_score += 0.2

        score += min(1.0, structure_score) * 0.20

        # 4. 完整性分数 (15%)：句子完整性
        sentences = re.split(r'[.!?。！？]', text)
        complete_sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        if len(sentences) > 0:
            completeness = len(complete_sentences) / len(sentences)
        else:
            completeness = 0

        score += completeness * 0.15

        # 5. 避免重复内容 (10%)
        words = text.split()
        unique_words = set(words)
        if len(words) > 0:
            uniqueness = len(unique_words) / len(words)
        else:
            uniqueness = 0

        score += uniqueness * 0.10

        return min(1.0, max(0.0, score))

    def get_best_chunks(self, chunks: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
        """获取质量最高的前k个chunks"""
        if not chunks:
            return []

        # 计算每个chunk的质量分数
        for chunk in chunks:
            chunk["quality_score"] = self.calculate_chunk_quality(chunk)

        # 按质量分数排序
        sorted_chunks = sorted(chunks, key=lambda x: x["quality_score"], reverse=True)

        # 返回前k个
        return sorted_chunks[:top_k]

# 嵌入服务
class EmbeddingService:
    def __init__(self):
        self.model_name = "local-embedding-model"
        self.embedding_dim = 768  # 常见的本地模型维度
        self.model = None

    def _load_model(self):
        """加载本地embedding模型"""
        if self.model is not None:
            return self.model

        try:
            # 尝试使用sentence-transformers
            from sentence_transformers import SentenceTransformer
            # 常用的中文embedding模型
            model_names = [
                "all-MiniLM-L6-v2",  # 英文模型，轻量级
                "paraphrase-multilingual-MiniLM-L12-v2",  # 多语言模型
                "distiluse-base-multilingual-cased"  # 多语言模型
            ]

            for model_name in model_names:
                try:
                    print(f"尝试加载模型: {model_name}")
                    self.model = SentenceTransformer(model_name)
                    self.model_name = model_name
                    self.embedding_dim = self.model.get_sentence_embedding_dimension()
                    print(f"✅ 成功加载模型: {model_name}, 维度: {self.embedding_dim}")
                    return self.model
                except Exception as e:
                    print(f"⚠️ 无法加载模型 {model_name}: {e}")
                    continue

            raise ImportError("未找到可用的sentence-transformers模型")

        except ImportError as e:
            print(f"⚠️ sentence-transformers未安装: {e}")
            # 使用transformers库作为备选
            try:
                from transformers import AutoTokenizer, AutoModel
                import torch

                # 使用BERT作为备选
                model_name = "bert-base-uncased"
                print(f"尝试使用transformers加载: {model_name}")

                self.tokenizer = AutoTokenizer.from_pretrained(model_name)
                self.model = AutoModel.from_pretrained(model_name)
                self.model_name = model_name
                self.embedding_dim = 768  # BERT维度
                print(f"✅ 成功加载transformers模型: {model_name}")
                return self.model

            except ImportError:
                print("⚠️ transformers未安装，使用模拟embedding")
                return None

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本embeddings"""
        try:
            model = self._load_model()

            if model is None:
                # 使用模拟embedding
                print("⚠️ 使用模拟embedding向量")
                return [[0.1] * self.embedding_dim for _ in texts]

            # 使用sentence-transformers
            if hasattr(model, 'encode'):
                embeddings = model.encode(texts, convert_to_tensor=False)
                return embeddings.tolist() if hasattr(embeddings, 'tolist') else embeddings

            # 使用transformers
            elif hasattr(self, 'tokenizer'):
                import torch
                embeddings = []

                for text in texts:
                    inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True, max_length=512)
                    with torch.no_grad():
                        outputs = model(**inputs)
                        # 使用CLS token的embedding
                        embedding = outputs.last_hidden_state[:, 0, :].squeeze().numpy()
                        embeddings.append(embedding.tolist())

                return embeddings

            else:
                print("⚠️ 模型加载异常，使用模拟embedding")
                return [[0.1] * self.embedding_dim for _ in texts]

        except Exception as e:
            print(f"❌ 生成embedding出错: {str(e)}")
            return [[0.0] * self.embedding_dim for _ in texts]

    async def generate_single_embedding(self, text: str) -> List[float]:
        """生成单个文本的embedding"""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else [0.0] * 1536

# 创建全局实例
document_processor = DocumentProcessor()
embedding_service = EmbeddingService()

# 完整的文档处理流程
async def process_document_complete(file_path: str, file_info: Dict[str, Any], return_best: Optional[int] = None) -> Dict[str, Any]:
    """完整的文档处理流程：提取文本 -> 分割 -> 生成embeddings -> 保存到向量存储"""
    try:
        # 导入向量存储（避免循环导入）
        from app.services.vector_store import vector_store

        # 1. 提取文本
        text = await document_processor.extract_text_from_file(file_path)

        if text.startswith("[Error]"):
            return {
                "success": False,
                "error": text,
                "file_info": file_info
            }

        # 2. 分割文本
        chunks = document_processor.chunk_text(text)

        if not chunks:
            return {
                "success": False,
                "error": "No text content found in document",
                "file_info": file_info
            }

        # 3. 生成embeddings
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = await embedding_service.generate_embeddings(chunk_texts)

        # 4. 组合结果
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunks.append({
                **chunk,
                "embedding": embeddings[i] if i < len(embeddings) else None,
                "embedding_model": embedding_service.model_name
            })

        # 5. 保存到向量存储
        chunk_ids = vector_store.add_document_chunks(file_path, file_info, processed_chunks)

        # 6. 按质量排序并筛选最佳chunks（如果指定了return_best）
        if return_best is not None and return_best > 0:
            best_chunks = document_processor.get_best_chunks(processed_chunks, return_best)
            final_chunks = best_chunks
            quality_filtered = True
        else:
            final_chunks = processed_chunks
            quality_filtered = False

        return {
            "success": True,
            "file_info": file_info,
            "original_text": text,
            "text_length": len(text),
            "total_chunks": len(chunks),
            "chunk_count": len(final_chunks),
            "chunks": final_chunks,
            "chunk_ids": chunk_ids,  # 新增：向量存储中的chunk IDs
            "quality_filtered": quality_filtered,
            "vector_store_stats": vector_store.get_stats(),  # 新增：向量存储统计
            "processing_stats": {
                "chunk_size": document_processor.chunk_size,
                "chunk_overlap": document_processor.chunk_overlap,
                "embedding_model": embedding_service.model_name,
                "embedding_dimension": embedding_service.embedding_dim,
                "return_best": return_best
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Processing failed: {str(e)}",
            "file_info": file_info
        }