"""
Retrieval Pipeline - Vector Search and Context Retrieval
Handles item, customer, and analytics retrieval
"""
import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import Engine, text
from sqlmodel import Session, select
from datetime import datetime, timedelta
from .config import config

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """Retrieves relevant context from database"""
    
    def __init__(self, engine: Engine):
        self.engine = engine
    
    def retrieve_items(
        self,
        query_embedding: List[float],
        user_id: int,
        top_k: int = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar items using vector search
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for filtering
            top_k: Number of results (default from config)
            threshold: Similarity threshold (default from config)
        
        Returns:
            List of similar items with metadata
        """
        top_k = config.retrieval.item_top_k if top_k is None else top_k
        threshold = config.retrieval.item_similarity_threshold if threshold is None else threshold
        
        start = time.time()
        
        try:
            with Session(self.engine) as session:
                # Vector similarity search using cosine distance
                query = text("""
                    SELECT 
                        id,
                        master_id,
                        names,
                        category,
                        price,
                        unit,
                        1 - (embedding <=> :embedding) as similarity
                    FROM items
                    WHERE owner_id = :user_id
                        AND embedding IS NOT NULL
                        AND (1 - (embedding <=> :embedding)) > :threshold
                    ORDER BY embedding <=> :embedding
                    LIMIT :top_k
                """)
                
                result = session.execute(
                    query,
                    {
                        "embedding": str(query_embedding),
                        "user_id": user_id,
                        "threshold": threshold,
                        "top_k": top_k
                    }
                )
                
                items = []
                for row in result:
                    items.append({
                        "id": row.id,
                        "master_id": row.master_id,
                        "names": row.names,
                        "category": row.category,
                        "price": row.price,
                        "unit": row.unit,
                        "similarity": float(row.similarity)
                    })
                
                duration = time.time() - start
                logger.info(f"Retrieved {len(items)} items in {duration*1000:.2f}ms")
                return items
                
        except Exception as e:
            logger.error(f"Item retrieval failed: {e}")
            return []
    
    def retrieve_customers(
        self,
        query_embedding: List[float],
        user_id: int,
        top_k: int = None,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar customers using vector search
        
        Args:
            query_embedding: Query embedding vector
            user_id: User ID for filtering
            top_k: Number of results (default from config)
            threshold: Similarity threshold (default from config)
        
        Returns:
            List of similar customers with purchase history
        """
        top_k = config.retrieval.customer_top_k if top_k is None else top_k
        threshold = config.retrieval.customer_similarity_threshold if threshold is None else threshold
        
        start = time.time()
        
        try:
            with Session(self.engine) as session:
                query = text("""
                    SELECT 
                        id,
                        phone_number,
                        name,
                        total_bills,
                        total_spent,
                        last_purchase_date,
                        1 - (embedding <=> :embedding) as similarity
                    FROM customers
                    WHERE owner_id = :user_id
                        AND embedding IS NOT NULL
                        AND (1 - (embedding <=> :embedding)) > :threshold
                    ORDER BY embedding <=> :embedding
                    LIMIT :top_k
                """)
                
                result = session.execute(
                    query,
                    {
                        "embedding": str(query_embedding),
                        "user_id": user_id,
                        "threshold": threshold,
                        "top_k": top_k
                    }
                )
                
                customers = []
                for row in result:
                    customers.append({
                        "id": row.id,
                        "phone_number": row.phone_number,
                        "name": row.name,
                        "total_bills": row.total_bills,
                        "total_spent": float(row.total_spent),
                        "last_purchase_date": row.last_purchase_date.isoformat() if row.last_purchase_date else None,
                        "similarity": float(row.similarity)
                    })
                
                duration = time.time() - start
                logger.info(f"Retrieved {len(customers)} customers in {duration*1000:.2f}ms")
                return customers
                
        except Exception as e:
            logger.error(f"Customer retrieval failed: {e}")
            return []
    
    def retrieve_analytics(
        self,
        user_id: int,
        days: int = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve business analytics
        
        Args:
            user_id: User ID
            days: Number of days (default from config)
        
        Returns:
            Analytics summary dict or None
        """
        days = days or config.analytics.default_period_days
        start = time.time()
        
        try:
            with Session(self.engine) as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Total revenue and bill count
                revenue_query = text("""
                    SELECT 
                        COUNT(*) as bill_count,
                        COALESCE(SUM(total_amount), 0) as total_revenue,
                        COALESCE(AVG(total_amount), 0) as avg_bill_value
                    FROM bills
                    WHERE owner_id = :user_id
                        AND bill_date >= :cutoff_date
                """)
                
                revenue_result = session.execute(
                    revenue_query,
                    {"user_id": user_id, "cutoff_date": cutoff_date}
                ).first()
                
                # Top selling items
                top_items_query = text("""
                    SELECT 
                        item_name,
                        item_category,
                        COUNT(*) as sale_count,
                        SUM(quantity) as total_quantity,
                        SUM(total_price) as total_revenue
                    FROM sale_items
                    WHERE owner_id = :user_id
                        AND sale_date >= :cutoff_date
                    GROUP BY item_name, item_category
                    ORDER BY total_revenue DESC
                    LIMIT :top_count
                """)
                
                top_items_result = session.execute(
                    top_items_query,
                    {
                        "user_id": user_id,
                        "cutoff_date": cutoff_date,
                        "top_count": config.analytics.top_items_count
                    }
                ).all()
                
                analytics = {
                    "period_days": days,
                    "total_revenue": float(revenue_result.total_revenue),
                    "bill_count": revenue_result.bill_count,
                    "avg_bill_value": float(revenue_result.avg_bill_value),
                    "top_items": [
                        {
                            "name": item.item_name,
                            "category": item.item_category,
                            "sale_count": item.sale_count,
                            "total_quantity": float(item.total_quantity),
                            "total_revenue": float(item.total_revenue)
                        }
                        for item in top_items_result
                    ]
                }
                
                duration = time.time() - start
                logger.info(f"Retrieved analytics in {duration*1000:.2f}ms")
                return analytics
                
        except Exception as e:
            logger.error(f"Analytics retrieval failed: {e}")
            return None
    
    async def retrieve_all_parallel(
        self,
        query_embedding: List[float],
        user_id: int,
        include_analytics: bool = True,
        include_customers: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve all context in parallel
        
        Args:
            query_embedding: Query embedding
            user_id: User ID
            include_analytics: Include analytics context
            include_customers: Include customer context
        
        Returns:
            Dictionary with items, customers, analytics, and timings
        """
        import asyncio
        
        start = time.time()
        
        # Create tasks
        tasks = []
        task_map = {}
        
        # Items (always included)
        tasks.append(asyncio.to_thread(
            self.retrieve_items,
            query_embedding,
            user_id
        ))
        task_map[len(tasks)-1] = "items"
        
        # Customers (optional)
        if include_customers:
            tasks.append(asyncio.to_thread(
                self.retrieve_customers,
                query_embedding,
                user_id
            ))
            task_map[len(tasks)-1] = "customers"
        
        # Analytics (optional)
        if include_analytics:
            tasks.append(asyncio.to_thread(
                self.retrieve_analytics,
                user_id
            ))
            task_map[len(tasks)-1] = "analytics"
        
        # Execute in parallel
        results = await asyncio.gather(*tasks)
        
        # Map results
        output = {
            "items": [],
            "customers": [],
            "analytics": None,
            "timings": {
                "total_parallel": time.time() - start
            }
        }
        
        for idx, result in enumerate(results):
            key = task_map[idx]
            output[key] = result
        
        return output
