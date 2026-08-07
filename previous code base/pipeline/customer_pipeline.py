"""
Customer Pipeline - Customer Embedding Management
Handles customer name embeddings and the customer_embedding table
"""

import time
import json
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime

from .embedding_pipeline import embedding_pipeline
from .logger import logger


class CustomerPipeline:
    """
    Manages customer embeddings and the customer_embedding table
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.embedding_service = embedding_pipeline
        self._ensure_customer_embedding_table()
    
    def _ensure_customer_embedding_table(self):
        """Create customer_embedding table if it doesn't exist"""
        try:
            with self.engine.connect() as conn:
                # Check if table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'customer_embedding'
                    )
                """))
                
                table_exists = result.fetchone()[0]
                
                if not table_exists:
                    print("[INFO] Creating customer_embedding table...")
                    
                    # Create table
                    conn.execute(text("""
                        CREATE TABLE customer_embedding (
                            id SERIAL PRIMARY KEY,
                            owner_id INTEGER NOT NULL,
                            customer_name VARCHAR(255) NOT NULL,
                            customer_phone VARCHAR(20),
                            bill_count INTEGER DEFAULT 0,
                            total_spent FLOAT DEFAULT 0.0,
                            last_purchase TIMESTAMP,
                            embedding VECTOR(384),
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(owner_id, customer_name)
                        )
                    """))
                    
                    # Create indexes
                    conn.execute(text("""
                        CREATE INDEX idx_customer_embedding_owner 
                        ON customer_embedding(owner_id)
                    """))
                    
                    conn.execute(text("""
                        CREATE INDEX idx_customer_embedding_vector 
                        ON customer_embedding 
                        USING ivfflat (embedding vector_cosine_ops) 
                        WITH (lists = 100)
                    """))
                    
                    conn.commit()
                    print("[OK] customer_embedding table created successfully")
                else:
                    print("[OK] customer_embedding table already exists")
                    
        except Exception as e:
            print(f"[WARN] Could not create customer_embedding table: {e}")
    
    def sync_customer_embeddings(self, user_id: int) -> Dict[str, Any]:
        """
        Sync customer embeddings from bills table
        Creates/updates embeddings for all customers of a user
        
        Args:
            user_id: Owner ID
            
        Returns:
            {
                'success': bool,
                'customers_processed': int,
                'embeddings_created': int,
                'embeddings_updated': int,
                'errors': int
            }
        """
        print(f"[INFO] Syncing customer embeddings for user {user_id}")
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Get unique customers from bills (parameterized)
                query = text("""
                    SELECT 
                        customer_name,
                        customer_phone,
                        COUNT(*) as bill_count,
                        SUM(total_amount) as total_spent,
                        MAX(bill_date) as last_purchase
                    FROM bill
                    WHERE owner_id = :user_id
                        AND customer_name IS NOT NULL
                        AND customer_name != ''
                        AND customer_name != 'Walk-in'
                    GROUP BY customer_name, customer_phone
                """)
                result = conn.execute(query, {"user_id": user_id})
                
                customers = result.fetchall()
                
                if not customers:
                    return {
                        'success': True,
                        'customers_processed': 0,
                        'embeddings_created': 0,
                        'embeddings_updated': 0,
                        'errors': 0,
                        'time': time.time() - start_time
                    }
                
                print(f"[INFO] Found {len(customers)} unique customers")
                
                created = 0
                updated = 0
                errors = 0
                
                for customer in customers:
                    try:
                        customer_name = customer.customer_name
                        customer_phone = customer.customer_phone
                        bill_count = customer.bill_count
                        total_spent = float(customer.total_spent)
                        last_purchase = customer.last_purchase
                        
                        # Generate embedding
                        embedding = self.embedding_service.generate_customer_embedding(customer_name)
                        
                        if not embedding:
                            errors += 1
                            continue
                        
                        embedding_str = '[' + ','.join(map(str, embedding)) + ']'
                        
                        # Check if customer exists (parameterized)
                        check_query = text("""
                            SELECT id FROM customer_embedding
                            WHERE owner_id = :user_id
                                AND customer_name = :customer_name
                        """)
                        check_result = conn.execute(check_query, {
                            "user_id": user_id,
                            "customer_name": customer_name
                        })
                        
                        existing = check_result.fetchone()
                        
                        if existing:
                            # Update existing (parameterized)
                            update_query = text("""
                                UPDATE customer_embedding
                                SET 
                                    customer_phone = :phone,
                                    bill_count = :bill_count,
                                    total_spent = :total_spent,
                                    last_purchase = :last_purchase,
                                    embedding = :embedding::vector,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = :id
                            """)
                            conn.execute(update_query, {
                                "phone": customer_phone or '',
                                "bill_count": bill_count,
                                "total_spent": total_spent,
                                "last_purchase": last_purchase.isoformat(),
                                "embedding": embedding_str,
                                "id": existing.id
                            })
                            updated += 1
                        else:
                            # Insert new (parameterized)
                            insert_query = text("""
                                INSERT INTO customer_embedding 
                                (owner_id, customer_name, customer_phone, bill_count, 
                                 total_spent, last_purchase, embedding)
                                VALUES 
                                (:user_id, :customer_name, :phone, :bill_count, 
                                 :total_spent, :last_purchase, :embedding::vector)
                            """)
                            conn.execute(insert_query, {
                                "user_id": user_id,
                                "customer_name": customer_name,
                                "phone": customer_phone or '',
                                "bill_count": bill_count,
                                "total_spent": total_spent,
                                "last_purchase": last_purchase.isoformat(),
                                "embedding": embedding_str
                            })
                            created += 1
                        
                    except Exception as e:
                        print(f"[ERROR] Failed to process customer '{customer.customer_name}': {e}")
                        errors += 1
                        continue
                
                conn.commit()
                
                elapsed = time.time() - start_time
                
                print(f"[OK] Customer sync complete: {created} created, {updated} updated, {errors} errors")
                print(f"[OK] Time: {elapsed:.2f}s")
                
                return {
                    'success': True,
                    'customers_processed': len(customers),
                    'embeddings_created': created,
                    'embeddings_updated': updated,
                    'errors': errors,
                    'time': elapsed
                }
                
        except Exception as e:
            logger.log_error("Customer Sync", e)
            return {
                'success': False,
                'error': str(e),
                'customers_processed': 0,
                'embeddings_created': 0,
                'embeddings_updated': 0,
                'errors': 0,
                'time': time.time() - start_time
            }
    
    def sync_all_users(self) -> Dict[str, Any]:
        """
        Sync customer embeddings for all users
        
        Returns:
            {
                'success': bool,
                'users_processed': int,
                'total_customers': int,
                'total_created': int,
                'total_updated': int,
                'total_errors': int
            }
        """
        print("[INFO] Syncing customer embeddings for all users...")
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Get all user IDs
                result = conn.execute(text("SELECT id FROM \"user\" WHERE is_active = true"))
                users = result.fetchall()
                
                print(f"[INFO] Found {len(users)} active users")
                
                total_customers = 0
                total_created = 0
                total_updated = 0
                total_errors = 0
                
                for user in users:
                    user_id = user.id
                    print(f"\n[INFO] Processing user {user_id}...")
                    
                    result = self.sync_customer_embeddings(user_id)
                    
                    if result['success']:
                        total_customers += result['customers_processed']
                        total_created += result['embeddings_created']
                        total_updated += result['embeddings_updated']
                        total_errors += result['errors']
                
                elapsed = time.time() - start_time
                
                print(f"\n[OK] All users synced in {elapsed:.2f}s")
                print(f"[OK] Total: {total_customers} customers, {total_created} created, {total_updated} updated")
                
                return {
                    'success': True,
                    'users_processed': len(users),
                    'total_customers': total_customers,
                    'total_created': total_created,
                    'total_updated': total_updated,
                    'total_errors': total_errors,
                    'time': elapsed
                }
                
        except Exception as e:
            print(f"[ERROR] All users sync failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'users_processed': 0,
                'total_customers': 0,
                'total_created': 0,
                'total_updated': 0,
                'total_errors': 0,
                'time': time.time() - start_time
            }
    
    def get_customer_stats(self, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get customer embedding statistics"""
        try:
            with self.engine.connect() as conn:
                if user_id:
                    query = text("""
                        SELECT 
                            COUNT(*) as total_customers,
                            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings,
                            AVG(bill_count) as avg_bills,
                            AVG(total_spent) as avg_spent
                        FROM customer_embedding
                        WHERE owner_id = :user_id
                    """)
                    result = conn.execute(query, {"user_id": user_id})
                else:
                    query = text("""
                        SELECT 
                            COUNT(*) as total_customers,
                            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as with_embeddings,
                            AVG(bill_count) as avg_bills,
                            AVG(total_spent) as avg_spent
                        FROM customer_embedding
                    """)
                    result = conn.execute(query)
                
                row = result.fetchone()
                
                if row:
                    total = row.total_customers or 0
                    with_emb = row.with_embeddings or 0
                    coverage = (with_emb / total * 100) if total > 0 else 0
                    
                    return {
                        'total_customers': total,
                        'with_embeddings': with_emb,
                        'coverage_percent': round(coverage, 2),
                        'avg_bills_per_customer': round(float(row.avg_bills or 0), 2),
                        'avg_spent_per_customer': round(float(row.avg_spent or 0), 2)
                    }
                
                return {
                    'total_customers': 0,
                    'with_embeddings': 0,
                    'coverage_percent': 0,
                    'avg_bills_per_customer': 0,
                    'avg_spent_per_customer': 0
                }
                
        except Exception as e:
            print(f"[ERROR] Failed to get customer stats: {e}")
            return {
                'error': str(e),
                'total_customers': 0,
                'with_embeddings': 0,
                'coverage_percent': 0
            }

