CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;

-- Custom MiroFish tables (LightRAG manages its own tables automatically)
CREATE TABLE IF NOT EXISTS mirofish_ontology (
    graph_id VARCHAR(64) PRIMARY KEY,
    ontology_json JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
