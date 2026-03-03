文本 API
文本向量化（Embedding）
使用 OpenAI Embedding 模型将文本转换为高维向量，支持知识库检索、语义搜索、文本相似度计算等应用场景

API易 提供业界领先的文本向量化（Embedding）能力，使用 OpenAI 的 Embedding 模型将文本转换为高维向量表示。这是构建智能知识库、语义搜索、RAG（检索增强生成）系统的核心技术，具有超高并发能力和极低的使用成本。
🔍 文本向量化核心能力 将文本转换为数值向量，捕捉语义信息，实现高效的语义检索、相似度计算和智能推荐。
​
🌟 核心特性
🎯 OpenAI 顶级模型：text-embedding-3-large、text-embedding-3-small、text-embedding-ada-002
⚡ 超高并发：支持大规模并发请求，适合企业级应用
💰 极低成本：按量付费，价格低至 $0.02/百万 tokens
🔧 简单易用：兼容 OpenAI API 格式，无缝集成
📊 高质量向量：捕捉深层语义，检索准确度高
​
📋 支持的 Embedding 模型
模型名称	模型 ID	向量维度	价格	推荐场景
text-embedding-3-large	text-embedding-3-large	3072 维	$0.13/1M tokens	高精度语义检索
text-embedding-3-small ⭐	text-embedding-3-small	1536 维	$0.02/1M tokens	通用场景，性价比最高
text-embedding-ada-002	text-embedding-ada-002	1536 维	$0.10/1M tokens	经典模型，兼容性好
模型选择建议：
高精度需求：使用 text-embedding-3-large，适合专业知识库、法律文档等场景
通用场景：推荐 text-embedding-3-small，性价比最高，适合大多数应用
兼容性优先：使用 text-embedding-ada-002，与旧版本完全兼容
​
🚀 快速开始
​
1. 最简单示例 - 使用 curl 命令
curl https://api.apiyi.com/v1/embeddings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "input": "人工智能正在改变世界",
    "model": "text-embedding-3-small"
  }'
查看返回结果示例

​
2. 基础示例 - 使用 OpenAI SDK
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

def get_embedding(text, model="text-embedding-3-small"):
    """获取文本的向量表示"""
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding

# 使用示例
text = "人工智能正在改变世界"
embedding = get_embedding(text)

print(f"向量维度: {len(embedding)}")
print(f"向量前5个值: {embedding[:5]}")
​
3. 批量文本向量化
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

def batch_get_embeddings(texts, model="text-embedding-3-small"):
    """批量获取文本向量"""
    response = client.embeddings.create(
        input=texts,
        model=model
    )
    return [item.embedding for item in response.data]

# 批量处理
texts = [
    "机器学习是人工智能的核心技术",
    "深度学习推动了AI的发展",
    "自然语言处理让机器理解人类语言",
    "计算机视觉让机器看懂图像"
]

embeddings = batch_get_embeddings(texts)
print(f"成功向量化 {len(embeddings)} 条文本")
​
4. 使用 requests 库
import requests

def get_embedding_with_requests(text, model="text-embedding-3-small"):
    """使用 requests 库获取向量"""
    url = "https://api.apiyi.com/v1/embeddings"
    headers = {
        "Authorization": "Bearer YOUR_API_KEY",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "input": text
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        data = response.json()
        return data['data'][0]['embedding']
    else:
        print(f"错误: {response.status_code} - {response.text}")
        return None

# 使用示例
embedding = get_embedding_with_requests("人工智能技术")
print(f"向量维度: {len(embedding)}")
​
🎯 典型应用场景
​
1. 语义搜索引擎
import numpy as np
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

def cosine_similarity(a, b):
    """计算余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def semantic_search(query, documents, top_k=3):
    """语义搜索"""
    # 获取查询和文档的向量
    all_texts = [query] + documents
    response = client.embeddings.create(
        input=all_texts,
        model="text-embedding-3-small"
    )

    embeddings = [item.embedding for item in response.data]
    query_embedding = embeddings[0]
    doc_embeddings = embeddings[1:]

    # 计算相似度
    similarities = [
        cosine_similarity(query_embedding, doc_emb)
        for doc_emb in doc_embeddings
    ]

    # 排序并返回最相关的文档
    ranked_indices = np.argsort(similarities)[::-1][:top_k]

    results = [
        {
            "document": documents[i],
            "similarity": similarities[i]
        }
        for i in ranked_indices
    ]

    return results

# 使用示例
documents = [
    "Python是一种高级编程语言",
    "机器学习需要大量数据",
    "深度学习是AI的重要分支",
    "JavaScript用于网页开发"
]

query = "人工智能和机器学习"
results = semantic_search(query, documents)

for i, result in enumerate(results, 1):
    print(f"{i}. {result['document']} (相似度: {result['similarity']:.4f})")
​
2. 构建向量数据库
import numpy as np
import json
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

class SimpleVectorDB:
    """简单的向量数据库实现"""

    def __init__(self, model="text-embedding-3-small"):
        self.model = model
        self.documents = []
        self.embeddings = []

    def add_documents(self, docs):
        """添加文档到向量库"""
        # 获取向量
        response = client.embeddings.create(
            input=docs,
            model=self.model
        )

        embeddings = [item.embedding for item in response.data]

        self.documents.extend(docs)
        self.embeddings.extend(embeddings)

        print(f"已添加 {len(docs)} 条文档到向量库")

    def search(self, query, top_k=5):
        """搜索最相关的文档"""
        # 获取查询向量
        response = client.embeddings.create(
            input=query,
            model=self.model
        )
        query_embedding = response.data[0].embedding

        # 计算相似度
        similarities = []
        for doc_embedding in self.embeddings:
            sim = np.dot(query_embedding, doc_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_embedding)
            )
            similarities.append(sim)

        # 排序
        ranked_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            {
                "document": self.documents[i],
                "similarity": similarities[i]
            }
            for i in ranked_indices
        ]

    def save(self, filepath):
        """保存向量库到文件"""
        data = {
            "documents": self.documents,
            "embeddings": self.embeddings,
            "model": self.model
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def load(self, filepath):
        """从文件加载向量库"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.documents = data['documents']
        self.embeddings = data['embeddings']
        self.model = data['model']

# 使用示例
db = SimpleVectorDB()

# 添加知识库文档
knowledge_base = [
    "机器学习是让计算机从数据中学习的技术",
    "深度学习使用多层神经网络处理复杂模式",
    "自然语言处理帮助计算机理解人类语言",
    "强化学习通过奖励机制训练智能体"
]

db.add_documents(knowledge_base)

# 搜索
results = db.search("什么是深度学习?", top_k=2)
for result in results:
    print(f"相似度 {result['similarity']:.4f}: {result['document']}")
​
3. 文本去重和聚类
import numpy as np
from sklearn.cluster import KMeans
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

def deduplicate_texts(texts, threshold=0.95):
    """基于向量相似度去重"""
    # 获取所有文本的向量
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    embeddings = np.array([item.embedding for item in response.data])

    # 计算相似度矩阵
    unique_indices = [0]  # 保留第一个

    for i in range(1, len(texts)):
        is_duplicate = False
        for j in unique_indices:
            similarity = np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
            )
            if similarity > threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_indices.append(i)

    return [texts[i] for i in unique_indices]

def cluster_texts(texts, n_clusters=3):
    """文本聚类"""
    # 获取向量
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    embeddings = np.array([item.embedding for item in response.data])

    # K-means 聚类
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)

    # 组织结果
    clusters = {i: [] for i in range(n_clusters)}
    for text, label in zip(texts, labels):
        clusters[label].append(text)

    return clusters

# 使用示例 - 去重
texts_with_duplicates = [
    "人工智能正在改变世界",
    "AI技术正在改变我们的世界",  # 语义相似
    "机器学习是AI的核心",
    "深度学习推动AI发展"
]

unique_texts = deduplicate_texts(texts_with_duplicates, threshold=0.9)
print(f"去重后剩余 {len(unique_texts)} 条文本")

# 使用示例 - 聚类
texts_to_cluster = [
    "Python编程语言",
    "机器学习算法",
    "Java开发框架",
    "深度学习模型",
    "JavaScript前端开发",
    "神经网络训练"
]

clusters = cluster_texts(texts_to_cluster, n_clusters=2)
for cluster_id, cluster_texts in clusters.items():
    print(f"\n聚类 {cluster_id}:")
    for text in cluster_texts:
        print(f"  - {text}")
​
4. RAG（检索增强生成）系统
from openai import OpenAI
import numpy as np

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

class RAGSystem:
    """简单的 RAG 系统实现"""

    def __init__(self):
        self.knowledge_base = []
        self.embeddings = []

    def add_knowledge(self, documents):
        """添加知识到知识库"""
        response = client.embeddings.create(
            input=documents,
            model="text-embedding-3-small"
        )

        embeddings = [item.embedding for item in response.data]
        self.knowledge_base.extend(documents)
        self.embeddings.extend(embeddings)

    def retrieve(self, query, top_k=3):
        """检索相关文档"""
        # 获取查询向量
        response = client.embeddings.create(
            input=query,
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding

        # 计算相似度
        similarities = [
            np.dot(query_embedding, doc_emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
            )
            for doc_emb in self.embeddings
        ]

        # 获取最相关的文档
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [self.knowledge_base[i] for i in top_indices]

    def generate_answer(self, question):
        """生成答案"""
        # 检索相关知识
        relevant_docs = self.retrieve(question, top_k=3)

        # 构建 prompt
        context = "\n".join(relevant_docs)
        prompt = f"""基于以下知识回答问题：

知识库内容：
{context}

问题：{question}

请基于上述知识给出准确的回答："""

        # 生成回答
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        return response.choices[0].message.content

# 使用示例
rag = RAGSystem()

# 添加知识库
knowledge = [
    "GPT-4 是 OpenAI 开发的大型语言模型，具有强大的理解和生成能力。",
    "Claude 是 Anthropic 开发的 AI 助手，注重安全性和有用性。",
    "Gemini 是 Google 开发的多模态 AI 模型，支持文本、图像和视频。",
    "LLaMA 是 Meta 开发的开源大语言模型系列。"
]

rag.add_knowledge(knowledge)

# 提问并生成答案
question = "GPT-4 是谁开发的？"
answer = rag.generate_answer(question)
print(f"问题: {question}")
print(f"答案: {answer}")
​
5. 推荐系统
import numpy as np
from openai import OpenAI

client = OpenAI(
    api_key="YOUR_API_KEY",
    base_url="https://api.apiyi.com/v1"
)

class ContentRecommender:
    """基于内容的推荐系统"""

    def __init__(self):
        self.items = []
        self.embeddings = []

    def add_items(self, items):
        """添加物品（标题、描述等）"""
        response = client.embeddings.create(
            input=items,
            model="text-embedding-3-small"
        )

        embeddings = [item.embedding for item in response.data]
        self.items.extend(items)
        self.embeddings.extend(embeddings)

    def recommend(self, user_preference, top_k=5):
        """基于用户偏好推荐"""
        # 获取用户偏好向量
        response = client.embeddings.create(
            input=user_preference,
            model="text-embedding-3-small"
        )
        pref_embedding = response.data[0].embedding

        # 计算相似度
        similarities = [
            np.dot(pref_embedding, item_emb) / (
                np.linalg.norm(pref_embedding) * np.linalg.norm(item_emb)
            )
            for item_emb in self.embeddings
        ]

        # 排序推荐
        top_indices = np.argsort(similarities)[::-1][:top_k]

        return [
            {
                "item": self.items[i],
                "score": similarities[i]
            }
            for i in top_indices
        ]

# 使用示例
recommender = ContentRecommender()

# 添加商品
products = [
    "MacBook Pro M3 专业笔记本电脑 高性能办公",
    "iPhone 15 Pro 智能手机 拍照摄影",
    "AirPods Pro 无线降噪耳机",
    "iPad Air 平板电脑 娱乐学习",
    "ThinkPad X1 商务笔记本 办公利器"
]

recommender.add_items(products)

# 推荐
user_pref = "我想买一台用于编程和办公的笔记本电脑"
recommendations = recommender.recommend(user_pref, top_k=3)

print(f"用户需求: {user_pref}\n")
print("推荐商品:")
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec['item']} (匹配度: {rec['score']:.4f})")
​
💡 最佳实践
​
1. 文本预处理
import re

def preprocess_text(text):
    """文本预处理"""
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)

    # 去除特殊字符（可选）
    # text = re.sub(r'[^\w\s]', '', text)

    # 转小写（可选，取决于场景）
    # text = text.lower()

    return text.strip()

# 长文本分块
def chunk_text(text, max_tokens=500, overlap=50):
    """将长文本分割成小块"""
    words = text.split()
    chunks = []

    for i in range(0, len(words), max_tokens - overlap):
        chunk = ' '.join(words[i:i + max_tokens])
        chunks.append(chunk)

    return chunks

# 使用示例
long_text = """这是一段很长的文本..."""
chunks = chunk_text(long_text, max_tokens=200)

# 为每个分块获取向量
embeddings = batch_get_embeddings(chunks)
​
2. 缓存机制
import hashlib
import pickle
import os

class EmbeddingCache:
    """向量缓存系统"""

    def __init__(self, cache_dir="./embedding_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_key(self, text, model):
        """生成缓存键"""
        content = f"{text}_{model}"
        return hashlib.md5(content.encode()).hexdigest()

    def get(self, text, model):
        """获取缓存的向量"""
        cache_key = self._get_cache_key(text, model)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        if os.path.exists(cache_file):
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        return None

    def set(self, text, model, embedding):
        """保存向量到缓存"""
        cache_key = self._get_cache_key(text, model)
        cache_file = os.path.join(self.cache_dir, f"{cache_key}.pkl")

        with open(cache_file, 'wb') as f:
            pickle.dump(embedding, f)

    def clear(self):
        """清空缓存"""
        for file in os.listdir(self.cache_dir):
            os.remove(os.path.join(self.cache_dir, file))

# 使用缓存的向量获取函数
cache = EmbeddingCache()

def get_embedding_cached(text, model="text-embedding-3-small"):
    """带缓存的向量获取"""
    # 尝试从缓存获取
    cached = cache.get(text, model)
    if cached is not None:
        return cached

    # 调用 API
    response = client.embeddings.create(input=text, model=model)
    embedding = response.data[0].embedding

    # 保存到缓存
    cache.set(text, model, embedding)

    return embedding
​
3. 错误处理和重试
import time
from openai import OpenAI

def get_embedding_with_retry(text, model="text-embedding-3-small", max_retries=3):
    """带重试机制的向量获取"""
    client = OpenAI(
        api_key="YOUR_API_KEY",
        base_url="https://api.apiyi.com/v1"
    )

    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding

        except Exception as e:
            print(f"尝试 {attempt + 1}/{max_retries} 失败: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
            else:
                raise

    return None
​
4. 批处理优化
def batch_process_large_dataset(texts, batch_size=100, model="text-embedding-3-small"):
    """大数据集批量处理"""
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        print(f"处理批次 {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")

        try:
            response = client.embeddings.create(
                input=batch,
                model=model
            )
            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

            # 避免速率限制
            time.sleep(0.1)

        except Exception as e:
            print(f"批次处理失败: {e}")
            # 可以选择重试或跳过

    return all_embeddings
​
🔧 高级技巧
​
1. 多语言支持
# OpenAI Embedding 模型天然支持多语言
multilingual_texts = [
    "人工智能改变世界",           # 中文
    "AI is changing the world",  # 英文
    "L'IA change le monde",      # 法文
    "AIが世界を変える"            # 日文
]

embeddings = batch_get_embeddings(multilingual_texts)

# 可以跨语言计算相似度
sim = cosine_similarity(embeddings[0], embeddings[1])
print(f"中英文相似度: {sim:.4f}")
​
2. 维度归一化
import numpy as np

def normalize_embedding(embedding):
    """L2 归一化"""
    norm = np.linalg.norm(embedding)
    return embedding / norm if norm > 0 else embedding

# 归一化后可以直接用点积计算余弦相似度
emb1_normalized = normalize_embedding(embedding1)
emb2_normalized = normalize_embedding(embedding2)
similarity = np.dot(emb1_normalized, emb2_normalized)
​
3. 使用不同维度
# text-embedding-3-large 支持自定义维度
response = client.embeddings.create(
    input="示例文本",
    model="text-embedding-3-large",
    dimensions=1024  # 可以指定维度，最大 3072
)

# 更小的维度可以节省存储和计算成本
​
📊 性能对比
特性	text-embedding-3-large	text-embedding-3-small	text-embedding-ada-002
向量维度	3072	1536	1536
准确度	⭐⭐⭐⭐⭐	⭐⭐⭐⭐	⭐⭐⭐
速度	⭐⭐⭐	⭐⭐⭐⭐⭐	⭐⭐⭐⭐
价格	$0.13/1M tokens	$0.02/1M tokens	$0.10/1M tokens
推荐场景	高精度检索	通用场景	兼容旧版
​
💰 成本优化建议
选择合适的模型
通用场景使用 text-embedding-3-small（最便宜）
高精度需求才使用 text-embedding-3-large
批量处理
尽量批量发送请求，减少网络开销
单次请求最多支持数千条文本
缓存策略
对重复文本使用缓存，避免重复计算
存储向量结果，减少 API 调用
文本预处理
去除无用信息，减少 token 消耗
合理分块，避免超长文本
​
🚨 注意事项
文本长度：单个文本不要超过模型的 token 限制（通常 8191 tokens）
批量限制：单次请求建议不超过 2048 条文本
速率限制：注意 API 的速率限制，必要时添加延迟
向量存储：合理选择向量数据库（如 Pinecone、Milvus、Weaviate）
相似度计算：推荐使用余弦相似度，效果最好
​
🔗 相关资源
完整代码示例
API 定价说明
向量数据库选型指南
💡 小贴士：Embedding 是构建智能应用的基础能力。推荐从 text-embedding-3-small 开始，它在性能和成本之间达到了最佳平衡。对于企业级应用，建议结合专业的向量数据库（如 Pinecone、Milvus）使用。