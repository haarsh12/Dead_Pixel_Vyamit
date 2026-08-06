-- ============================================
-- SUPABASE DATABASE SETUP SCRIPT
-- ============================================
-- Run this in Supabase SQL Editor to setup your database

-- 1. Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Verify pgvector is enabled
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 3. Check database is ready
SELECT version();

-- ============================================
-- Tables will be created automatically by the backend
-- on first run via SQLModel
-- ============================================

-- Expected tables:
-- - users (shop owners)
-- - otps (authentication codes)
-- - items (inventory with vector embeddings)
-- - bills (transaction history)
-- - sale_items (analytics data)
-- - customers (customer profiles with embeddings)

-- ============================================
-- Optional: Create indexes for better performance
-- ============================================

-- These will be created automatically, but you can verify:
-- CREATE INDEX IF NOT EXISTS idx_items_owner_id ON items(owner_id);
-- CREATE INDEX IF NOT EXISTS idx_items_embedding_ivfflat ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
-- CREATE INDEX IF NOT EXISTS idx_customers_owner_phone ON customers(owner_id, phone_number);
-- CREATE INDEX IF NOT EXISTS idx_bills_owner_date ON bills(owner_id, bill_date);

-- ============================================
-- Check tables after backend creates them
-- ============================================

-- Run after starting backend:
-- SELECT tablename FROM pg_tables WHERE schemaname = 'public';

-- Check vector dimensions:
-- SELECT pg_typeof(embedding) FROM items LIMIT 1;

-- ============================================
-- DONE! Start your backend with:
-- python main.py
-- ============================================
