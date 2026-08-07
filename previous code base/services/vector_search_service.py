"""
Vector Search Service — RAG-based inventory search with multilingual embeddings.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine, text

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None

class VectorSearchService:
    _instance = None
    _model = None
    _engine = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorSearchService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize()
    
    def _initialize(self):
        """Initialize the service (singleton pattern) - Production Ready"""
        print("[INFO] Initializing Vector Search Service...")
        
        try:
            # Database connection (same URL rules as app.db.database)
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL not found in environment variables")
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            self._engine = create_engine(database_url, pool_pre_ping=True, pool_recycle=300)
            print("[OK] Database connection established for vector service.")
            
            # Test database connection and vector extension
            with self._engine.connect() as conn:
                # Test basic connection
                conn.execute(text("SELECT 1"))
                
                # Check vector extension
                result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'"))
                if not result.fetchone():
                    print("[WARN] Vector extension not found — attempting to enable...")
                    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                    conn.commit()
                    print("[OK] Vector extension enabled.")
                
                # Check embedding column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'item' AND column_name = 'embedding'
                """))
                if not result.fetchone():
                    print("[WARN] Embedding column not found — adding...")
                    conn.execute(text("ALTER TABLE item ADD COLUMN IF NOT EXISTS embedding vector(384)"))
                    conn.commit()
                    print("[OK] Embedding column added.")
                
                # Create vector index if not exists
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS item_embedding_idx 
                    ON item USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100)
                """))
                conn.commit()
                print("[OK] Vector index ensured.")
            
            # Load embedding model (OPTIONAL for Render deployment)
            print("[INFO] Loading intfloat/multilingual-e5-small model...")
            start_time = time.time()
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer("intfloat/multilingual-e5-small")
                load_time = time.time() - start_time
                print(f"[OK] Model loaded in {load_time:.2f}s")
                print(f"[INFO] Model embedding dimension: {self._model.get_sentence_embedding_dimension()}")
                self._initialized = True
                print("[OK] Vector Search Service initialized successfully.")
            except ImportError as ie:
                print(f"[WARN] sentence-transformers not installed ({ie})")
                print("[INFO] Vector search disabled. Use Gemini API embeddings via EMBEDDING_PROVIDER=2")
                print("[INFO] Core features (voice, LLM, inventory) remain functional")
                self._model = None
                self._initialized = False
            except Exception as model_err:
                print(f"[WARN] Vector model loading failed ({model_err})")
                print("[INFO] Vector search unavailable. Core features still work.")
                self._model = None
                self._initialized = False
            
        except Exception as e:
            print(f"[WARN] Vector Search Service initialization skipped: {str(e)}")
            print("[WARN] Vector search will be unavailable. Core voice/LLM features still work.")
            self._initialized = False
    
    def search_items(
        self, 
        query: str, 
        top_k: int = 15, 
        similarity_threshold: float = 0.1,
        debug: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Search inventory items using vector similarity - Production Ready
        
        Args:
            query: Search query in any language (Hindi/English/Hinglish)
            top_k: Number of top matches to return (default: 15)
            similarity_threshold: Minimum similarity score (default: 0.1)
            debug: Enable debug output
            
        Returns:
            List of matching items with similarity scores
        """
        if not self._initialized or self._model is None:
            if debug:
                print("[WARN] Vector search unavailable (model not loaded)")
            return []
        
        if debug:
            print(f"[DEBUG] Vector search: '{query}' (top {top_k}, threshold {similarity_threshold})")
        
        try:
            # Generate query embedding
            query_text = f"query: {query}"
            start_time = time.time()
            query_embedding = self._model.encode(query_text, normalize_embeddings=True)
            embed_time = time.time() - start_time
            
            if debug:
                print(f"[DEBUG] Query embedded in {embed_time:.3f}s")
                print(f"[DEBUG] Embedding shape: {query_embedding.shape}")
                print(f"[DEBUG] First 3 values: {query_embedding[:3].round(4)}")
            
            # Search database using direct SQL (tested and working)
            with self._engine.connect() as conn:
                # Convert embedding to string format for PostgreSQL
                embedding_str = '[' + ','.join(map(str, query_embedding.tolist())) + ']'
                
                result = conn.execute(text(f"""
                    SELECT 
                        item.id,
                        item.master_id,
                        item.names,
                        item.category,
                        item.price,
                        item.unit,
                        1 - (item.embedding <=> '{embedding_str}'::vector) as similarity
                    FROM item
                    WHERE item.embedding IS NOT NULL
                        AND 1 - (item.embedding <=> '{embedding_str}'::vector) > {similarity_threshold}
                    ORDER BY item.embedding <=> '{embedding_str}'::vector
                    LIMIT {top_k}
                """))
                
                matches = result.fetchall()
                
                if debug:
                    print(f"[DEBUG] Found {len(matches)} matches above threshold {similarity_threshold}")
                
                # Convert to structured format
                results = []
                for i, match in enumerate(matches):
                    try:
                        # Parse names (handle both JSON string and plain string)
                        if match.names:
                            try:
                                names_list = json.loads(match.names) if isinstance(match.names, str) and match.names.startswith('[') else [match.names]
                            except json.JSONDecodeError:
                                names_list = [match.names]
                        else:
                            names_list = ["Unknown"]
                        
                        result_dict = {
                            'id': match.id,
                            'master_id': match.master_id,
                            'names': names_list,
                            'primary_name': names_list[0] if names_list else "Unknown",
                            'category': match.category,
                            'price': float(match.price) if match.price else 0.0,
                            'unit': match.unit,
                            'similarity': float(match.similarity),
                            'confidence': self._get_confidence_level(match.similarity),
                            'rank': i + 1
                        }
                        
                        results.append(result_dict)
                        
                        if debug:
                            band = "high" if match.similarity > 0.8 else "med" if match.similarity > 0.6 else "low"
                            print(f"   {i+1:2d}. [{band}] {result_dict['primary_name']:<20} | {match.similarity:.3f}")
                            if len(names_list) > 1:
                                alt_names = ", ".join(names_list[1:3])
                                print(f"       Also: {alt_names}")
                    
                    except Exception as e:
                        if debug:
                            print(f"[WARN] Error processing match {i}: {str(e)}")
                        continue
                
                return results
                
        except Exception as e:
            print(f"[ERROR] Vector search error: {str(e)}")
            if debug:
                import traceback
                traceback.print_exc()
            return []
    
    def _get_confidence_level(self, similarity: float) -> str:
        """Convert similarity score to confidence level"""
        if similarity >= 0.8:
            return "high"
        elif similarity >= 0.6:
            return "medium"
        elif similarity >= 0.4:
            return "low"
        else:
            return "very_low"
    
    def create_embedding_text(self, item_data: Dict[str, Any]) -> str:
        """Create optimized text for embedding generation"""
        try:
            # Parse names
            names_list = item_data.get('names', [])
            if isinstance(names_list, str):
                try:
                    names_list = json.loads(names_list) if names_list.startswith('[') else [names_list]
                except json.JSONDecodeError:
                    names_list = [names_list]
            
            # Create rich text with all names and metadata
            text_parts = [
                f"passage: {' '.join(names_list)}",  # All names
                f"category: {item_data.get('category', '')}",
                f"unit: {item_data.get('unit', '')}"
            ]
            
            # Add price if available
            price = item_data.get('price', 0)
            if price and price > 0:
                text_parts.append(f"price: ₹{price}")
            
            return " | ".join(text_parts)
            
        except Exception as e:
            print(f"[ERROR] Error creating embedding text: {str(e)}")
            return f"passage: {item_data.get('names', ['Unknown'])[0] if isinstance(item_data.get('names', []), list) else item_data.get('names', 'Unknown')}"
    
    def embed_item(self, item_data: Dict[str, Any]) -> Optional[List[float]]:
        """
        Generate embedding for a single item - Production Ready
        
        Args:
            item_data: Dictionary with item information
            
        Returns:
            Embedding vector as list of floats, or None if unavailable
        """
        if not self._initialized or self._model is None:
            return None
        
        try:
            embedding_text = self.create_embedding_text(item_data)
            
            # Generate embedding
            embedding = self._model.encode(embedding_text, normalize_embeddings=True)
            return embedding.tolist()
            
        except Exception as e:
            print(f"[ERROR] Embedding generation error: {str(e)}")
            return None
    
    def update_item_embedding(self, item_id: int, item_data: Dict[str, Any]) -> bool:
        """
        Update embedding for a specific item - Production Ready
        
        Args:
            item_id: Item ID to update
            item_data: Item data for embedding generation
            
        Returns:
            Success status
        """
        try:
            embedding = self.embed_item(item_data)
            if embedding is None:
                return False
            
            with self._engine.connect() as conn:
                conn.execute(text("""
                    UPDATE item 
                    SET embedding = :embedding 
                    WHERE id = :id
                """), {
                    "embedding": embedding,
                    "id": item_id
                })
                conn.commit()
            
            print(f"[OK] Updated embedding for item {item_id}")
            return True
            
        except Exception as e:
            print(f"[ERROR] Update embedding error for item {item_id}: {str(e)}")
            return False
    
    def embed_all_items(self, batch_size: int = 50) -> Dict[str, Any]:
        """
        Embed all items that don't have embeddings - Production Ready
        
        Args:
            batch_size: Number of items to process in each batch
            
        Returns:
            Dictionary with embedding statistics
        """
        print("[INFO] Starting batch embedding process...")
        
        try:
            with self._engine.connect() as conn:
                # Get items without embeddings
                result = conn.execute(text("""
                    SELECT id, master_id, names, category, price, unit 
                    FROM item 
                    WHERE embedding IS NULL
                    ORDER BY id
                """))
                
                items = result.fetchall()
                total_items = len(items)
                
                if total_items == 0:
                    return {
                        "success": True,
                        "message": "All items already have embeddings",
                        "total_items": 0,
                        "embedded_items": 0,
                        "failed_items": 0
                    }
                
                print(f"[INFO] Found {total_items} items to embed")
                
                embedded_count = 0
                failed_count = 0
                
                # Process in batches
                for i in range(0, total_items, batch_size):
                    batch = items[i:i + batch_size]
                    batch_num = (i // batch_size) + 1
                    total_batches = (total_items + batch_size - 1) // batch_size
                    
                    print(f"[INFO] Processing batch {batch_num}/{total_batches} ({len(batch)} items)")
                    
                    for item in batch:
                        try:
                            item_dict = {
                                'names': item.names,
                                'category': item.category,
                                'price': item.price,
                                'unit': item.unit
                            }
                            
                            embedding = self.embed_item(item_dict)
                            if embedding:
                                conn.execute(text("""
                                    UPDATE item 
                                    SET embedding = :embedding 
                                    WHERE id = :id
                                """), {
                                    "embedding": embedding,
                                    "id": item.id
                                })
                                embedded_count += 1
                            else:
                                failed_count += 1
                                print(f"[WARN] Failed to embed item {item.id}")
                                
                        except Exception as e:
                            failed_count += 1
                            print(f"[ERROR] Error embedding item {item.id}: {str(e)}")
                    
                    conn.commit()
                    print(f"[OK] Batch {batch_num} completed")
                
                return {
                    "success": True,
                    "message": f"Embedded {embedded_count} items successfully",
                    "total_items": total_items,
                    "embedded_items": embedded_count,
                    "failed_items": failed_count
                }
                
        except Exception as e:
            print(f"[ERROR] Batch embedding error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "total_items": 0,
                "embedded_items": 0,
                "failed_items": 0
            }
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get current embedding statistics"""
        try:
            with self._engine.connect() as conn:
                # Total items
                result = conn.execute(text("SELECT COUNT(*) as count FROM item"))
                total_items = result.fetchone().count
                
                # Items with embeddings
                result = conn.execute(text("SELECT COUNT(*) as count FROM item WHERE embedding IS NOT NULL"))
                items_with_embeddings = result.fetchone().count
                
                coverage = (items_with_embeddings / total_items * 100) if total_items > 0 else 0
                
                return {
                    'total_items': total_items,
                    'items_with_embeddings': items_with_embeddings,
                    'coverage_percent': round(coverage, 2),
                    'missing_embeddings': total_items - items_with_embeddings
                }
                
        except Exception as e:
            print(f"[ERROR] Error getting embedding stats: {str(e)}")
            return {
                'total_items': 0,
                'items_with_embeddings': 0,
                'coverage_percent': 0,
                'missing_embeddings': 0,
                'error': str(e)
            }
    
    def get_similar_items(self, item_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find items similar to a given item - Production Ready
        
        Args:
            item_id: Reference item ID
            top_k: Number of similar items to return
            
        Returns:
            List of similar items
        """
        try:
            with self._engine.connect() as conn:
                # Get the reference item's embedding
                result = conn.execute(text("""
                    SELECT embedding FROM item WHERE id = :item_id AND embedding IS NOT NULL
                """), {"item_id": item_id})
                
                ref_item = result.fetchone()
                if not ref_item:
                    return []
                
                # Find similar items
                embedding_str = '[' + ','.join(map(str, ref_item.embedding)) + ']'
                
                result = conn.execute(text(f"""
                    SELECT 
                        item.id,
                        item.master_id,
                        item.names,
                        item.category,
                        item.price,
                        item.unit,
                        1 - (item.embedding <=> '{embedding_str}'::vector) as similarity
                    FROM item
                    WHERE item.id != {item_id}
                        AND item.embedding IS NOT NULL
                    ORDER BY item.embedding <=> '{embedding_str}'::vector
                    LIMIT {top_k}
                """))
                
                matches = result.fetchall()
                
                results = []
                for match in matches:
                    try:
                        names_list = json.loads(match.names) if isinstance(match.names, str) and match.names.startswith('[') else [match.names]
                    except:
                        names_list = [match.names] if match.names else ["Unknown"]
                    
                    result_dict = {
                        'id': match.id,
                        'master_id': match.master_id,
                        'names': names_list,
                        'primary_name': names_list[0] if names_list else "Unknown",
                        'category': match.category,
                        'price': float(match.price) if match.price else 0.0,
                        'unit': match.unit,
                        'similarity': float(match.similarity)
                    }
                    
                    results.append(result_dict)
                
                return results
                
        except Exception as e:
            print(f"[ERROR] Similar items error: {str(e)}")
            return []

# Global instance - Production Ready Singleton
vector_search_service = VectorSearchService()