-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 文档元数据表（结构化存储，便于精确查询与统计）
CREATE TABLE IF NOT EXISTS doc_chunks (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_hash    TEXT        NOT NULL UNIQUE,   -- SHA256(text), 去重用
    project_id    TEXT,
    term          TEXT,
    year          SMALLINT,
    phase         TEXT,
    doc_type      TEXT,
    quality_level TEXT,
    artifact_type TEXT,
    section_path  TEXT,
    page_num      SMALLINT,
    source_file   TEXT,       -- MinIO object key
    text          TEXT        NOT NULL,
    -- 备用 dense 向量列（pgvector，1024 维 bge-m3）
    embedding     vector(1024),
    inserted_at   TIMESTAMPTZ DEFAULT now()
);

-- 为常用过滤字段建索引
CREATE INDEX IF NOT EXISTS idx_chunks_project  ON doc_chunks(project_id);
CREATE INDEX IF NOT EXISTS idx_chunks_term     ON doc_chunks(term);
CREATE INDEX IF NOT EXISTS idx_chunks_phase    ON doc_chunks(phase);
CREATE INDEX IF NOT EXISTS idx_chunks_year     ON doc_chunks(year);

-- 备用 HNSW 向量索引（如需切换到 pgvector 进行向量检索）
-- CREATE INDEX ON doc_chunks USING hnsw (embedding vector_cosine_ops)
-- WITH (m = 16, ef_construction = 64);
