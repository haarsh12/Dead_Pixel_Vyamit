"""
Retrieval Pipeline - Parallel Context Retrieval
Retrieves relevant items, analytics metrics, and customer history
"""

import time
import json
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import asyncio

from .config import config
from .logger import logger


class RetrievalPipeline:
    """
    Handles all retrieval operations:
    1. Item retrieval via PGVector
    2. Analytics metrics calculation
    3. Customer retrieval via PGVector + bill history
    """
    
    def __init__(self, engine, embedding_service):
        self.engine = engine
        self.embedding_service = embedding_service
        self.item_top_k = config.retrieval.item_top_k
        self.item_similarity_threshold = config.retrieval.item_similarity_threshold
        self.customer_top_k = config.retrieval.customer_top_k
        self.customer_similarity_threshold = config.retrieval.customer_similarity_threshold
        self.max_bills_per_customer = config.retrieval.max_bills_per_customer
        self.default_period_days = config.analytics.default_period_days
    
    def retrieve_items(self, query_embedding: List[float], user_id: int) -> Tuple[List[Dict[str, Any]], float]:
        """
        Retrieve top K most similar items using PGVector
        
        Returns:
            (items, retrieval_time)
        """
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Convert embedding to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                # Vector similarity search with user filter (using parameterized query)
                query = text("""
                    SELECT 
                        item.id,
                        item.master_id,
                        item.names,
                        item.category,
                        item.price,
                        item.unit,
                        item.owner_id,
                        1 - (item.embedding <=> :embedding::vector) as similarity
                    FROM item
                    WHERE item.owner_id = :user_id
                        AND item.embedding IS NOT NULL
                        AND item.price > 0
                        AND 1 - (item.embedding <=> :embedding::vector) > :threshold
                    ORDER BY item.embedding <=> :embedding::vector
                    LIMIT :top_k
                """)
                
                result = conn.execute(query, {
                    "embedding": embedding_str,
                    "user_id": user_id,
                    "threshold": self.item_similarity_threshold,
                    "top_k": self.item_top_k
                })
                
                matches = result.fetchall()
                
                # Format results
                items = []
                for match in matches:
                    try:
                        # Parse names from JSON
                        names_list = json.loads(match.names) if isinstance(match.names, str) and match.names.startswith('[') else [match.names]
                    except:
                        names_list = [match.names] if match.names else ["Unknown"]
                    
                    items.append({
                        'id': match.id,
                        'master_id': match.master_id,
                        'names': names_list,
                        'primary_name': names_list[0] if names_list else "Unknown",
                        'category': match.category,
                        'price': float(match.price) if match.price else 0.0,
                        'unit': match.unit,
                        'similarity': float(match.similarity),
                        'rank': len(items) + 1
                    })
                
                retrieval_time = time.time() - start_time
                return items, retrieval_time
                
        except Exception as e:
            logger.log_error("Item Retrieval", e)
            return [], time.time() - start_time
    
    def retrieve_analytics(self, user_id: int, days: Optional[int] = None) -> Tuple[Dict[str, Any], float]:
        """
        Calculate and retrieve business analytics metrics
        
        Returns:
            (metrics_dict, calculation_time)
        """
        start_time = time.time()
        
        if days is None:
            days = self.default_period_days
        
        try:
            with self.engine.connect() as conn:
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days)
                
                # 1. Revenue Summary
                revenue_query = text("""
                    SELECT 
                        COUNT(*) as total_bills,
                        COALESCE(SUM(total_amount), 0) as total_revenue,
                        COALESCE(AVG(total_amount), 0) as avg_bill_value
                    FROM bill
                    WHERE owner_id = :user_id
                        AND bill_date >= :start_date
                """)
                revenue_result = conn.execute(revenue_query, {
                    "user_id": user_id,
                    "start_date": start_date.isoformat()
                })
                revenue_row = revenue_result.fetchone()
                
                # 2. Inventory Count
                inventory_query = text("""
                    SELECT COUNT(*) as total_items
                    FROM item
                    WHERE owner_id = :user_id
                        AND price > 0
                """)
                inventory_result = conn.execute(inventory_query, {"user_id": user_id})
                inventory_row = inventory_result.fetchone()
                
                # 3. Top Selling Items
                top_items_query = text("""
                    SELECT 
                        item_name,
                        unit,
                        SUM(quantity) as total_quantity,
                        COUNT(*) as times_sold,
                        SUM(total_price) as total_revenue
                    FROM saleitem
                    WHERE owner_id = :user_id
                        AND sale_date >= :start_date
                    GROUP BY item_name, unit
                    ORDER BY total_quantity DESC
                    LIMIT 10
                """)
                top_items_result = conn.execute(top_items_query, {
                    "user_id": user_id,
                    "start_date": start_date.isoformat()
                })
                top_items = top_items_result.fetchall()
                
                # 4. Category Breakdown
                category_query = text("""
                    SELECT 
                        item_category,
                        SUM(total_price) as category_revenue,
                        SUM(quantity) as category_quantity
                    FROM saleitem
                    WHERE owner_id = :user_id
                        AND sale_date >= :start_date
                    GROUP BY item_category
                    ORDER BY category_revenue DESC
                """)
                category_result = conn.execute(category_query, {
                    "user_id": user_id,
                    "start_date": start_date.isoformat()
                })
                categories = category_result.fetchall()
                
                # 5. Stock Status
                stock_query = text("""
                    SELECT 
                        COUNT(CASE WHEN price = 0 THEN 1 END) as out_of_stock,
                        COUNT(CASE WHEN price > 0 AND price < 10 THEN 1 END) as low_stock,
                        COUNT(*) as total_items
                    FROM item
                    WHERE owner_id = :user_id
                """)
                stock_result = conn.execute(stock_query, {"user_id": user_id})
                stock_row = stock_result.fetchone()
                
                # 6. Today's Sales
                today_query = text("""
                    SELECT 
                        COUNT(*) as today_bills,
                        COALESCE(SUM(total_amount), 0) as today_revenue
                    FROM bill
                    WHERE owner_id = :user_id
                        AND DATE(bill_date) = CURRENT_DATE
                """)
                today_result = conn.execute(today_query, {"user_id": user_id})
                today_row = today_result.fetchone()
                
                # Assemble metrics
                metrics = {
                    'period_days': days,
                    'summary': {
                        'total_revenue': float(revenue_row.total_revenue) if revenue_row else 0.0,
                        'total_bills': int(revenue_row.total_bills) if revenue_row else 0,
                        'average_bill_value': float(revenue_row.avg_bill_value) if revenue_row else 0.0,
                        'total_inventory_items': int(inventory_row.total_items) if inventory_row else 0,
                        'today_revenue': float(today_row.today_revenue) if today_row else 0.0,
                        'today_bills': int(today_row.today_bills) if today_row else 0,
                    },
                    'stock_status': {
                        'out_of_stock': int(stock_row.out_of_stock) if stock_row else 0,
                        'low_stock': int(stock_row.low_stock) if stock_row else 0,
                        'in_stock': int(stock_row.total_items) if stock_row else 0,
                    },
                    'top_selling_items': [
                        {
                            'name': item.item_name,
                            'unit': item.unit,
                            'quantity': float(item.total_quantity),
                            'times_sold': int(item.times_sold),
                            'revenue': float(item.total_revenue)
                        }
                        for item in top_items
                    ],
                    'category_breakdown': [
                        {
                            'category': cat.item_category,
                            'revenue': float(cat.category_revenue),
                            'quantity': float(cat.category_quantity)
                        }
                        for cat in categories
                    ]
                }
                
                retrieval_time = time.time() - start_time
                return metrics, retrieval_time
                
        except Exception as e:
            logger.log_error("Analytics Retrieval", e)
            return {}, time.time() - start_time
    
    def retrieve_customers(self, query_embedding: List[float], user_id: int) -> Tuple[List[Dict[str, Any]], float]:
        """
        Retrieve relevant customers using PGVector on customer names + their bill history
        
        Returns:
            (customers_with_history, retrieval_time)
        """
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                # Convert embedding to PostgreSQL vector format
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                # Check if customer_embedding table exists
                check_result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'customer_embedding'
                    )
                """))
                
                table_exists = check_result.fetchone()[0]
                
                if not table_exists:
                    # Fallback: Search customers by name from bills
                    customer_query = text("""
                        SELECT DISTINCT
                            customer_name,
                            customer_phone,
                            COUNT(*) as bill_count,
                            SUM(total_amount) as total_spent,
                            MAX(bill_date) as last_purchase
                        FROM bill
                        WHERE owner_id = :user_id
                            AND customer_name IS NOT NULL
                            AND customer_name != 'Walk-in'
                        GROUP BY customer_name, customer_phone
                        ORDER BY last_purchase DESC
                        LIMIT :top_k
                    """)
                    customer_result = conn.execute(customer_query, {
                        "user_id": user_id,
                        "top_k": self.customer_top_k
                    })
                else:
                    # Use vector search on customer embeddings
                    customer_query = text("""
                        SELECT 
                            ce.customer_name,
                            ce.customer_phone,
                            ce.bill_count,
                            ce.total_spent,
                            ce.last_purchase,
                            1 - (ce.embedding <=> :embedding::vector) as similarity
                        FROM customer_embedding ce
                        WHERE ce.owner_id = :user_id
                            AND ce.embedding IS NOT NULL
                            AND 1 - (ce.embedding <=> :embedding::vector) > :threshold
                        ORDER BY ce.embedding <=> :embedding::vector
                        LIMIT :top_k
                    """)
                    customer_result = conn.execute(customer_query, {
                        "embedding": embedding_str,
                        "user_id": user_id,
                        "threshold": self.customer_similarity_threshold,
                        "top_k": self.customer_top_k
                    })
                
                customers = []
                for row in customer_result.fetchall():
                    customer_name = row.customer_name
                    
                    # Get bill history for this customer (parameterized)
                    history_query = text("""
                        SELECT 
                            id,
                            bill_date,
                            total_amount,
                            total_items,
                            items_json,
                            payment_method
                        FROM bill
                        WHERE owner_id = :user_id
                            AND customer_name = :customer_name
                        ORDER BY bill_date DESC
                        LIMIT :max_bills
                    """)
                    history_result = conn.execute(history_query, {
                        "user_id": user_id,
                        "customer_name": customer_name,
                        "max_bills": self.max_bills_per_customer
                    })
                    
                    bills = []
                    for bill_row in history_result.fetchall():
                        bills.append({
                            'bill_id': bill_row.id,
                            'bill_date': bill_row.bill_date.isoformat() if bill_row.bill_date else None,
                            'total_amount': float(bill_row.total_amount),
                            'total_items': int(bill_row.total_items),
                            'payment_method': bill_row.payment_method,
                            'items': json.loads(bill_row.items_json) if bill_row.items_json else []
                        })
                    
                    customer_dict = {
                        'customer_name': customer_name,
                        'customer_phone': row.customer_phone,
                        'bill_count': int(row.bill_count),
                        'total_spent': float(row.total_spent),
                        'last_purchase': row.last_purchase.isoformat() if row.last_purchase else None,
                        'bills': bills
                    }
                    
                    # Add similarity if available
                    if table_exists and hasattr(row, 'similarity'):
                        customer_dict['similarity'] = float(row.similarity)
                    
                    customers.append(customer_dict)
                
                retrieval_time = time.time() - start_time
                return customers, retrieval_time
                
        except Exception as e:
            logger.log_error("Customer Retrieval", e)
            return [], time.time() - start_time
    
    async def retrieve_all_parallel(
        self, 
        query_embedding: List[float], 
        user_id: int,
        include_analytics: bool = True,
        include_customers: bool = True
    ) -> Dict[str, Any]:
        """
        Execute all retrievals in parallel for maximum performance
        
        Returns:
            {
                'items': [...],
                'analytics': {...},
                'customers': [...],
                'timings': {...}
            }
        """
        loop = asyncio.get_event_loop()
        
        # Execute in parallel
        tasks = [
            loop.run_in_executor(None, self.retrieve_items, query_embedding, user_id)
        ]
        
        if include_analytics:
            tasks.append(
                loop.run_in_executor(None, self.retrieve_analytics, user_id, None)
            )
        
        if include_customers:
            tasks.append(
                loop.run_in_executor(None, self.retrieve_customers, query_embedding, user_id)
            )
        
        # Wait for all
        results = await asyncio.gather(*tasks)
        
        # Unpack results
        items, item_time = results[0]
        
        idx = 1
        analytics = {}
        analytics_time = 0.0
        if include_analytics:
            analytics, analytics_time = results[idx]
            idx += 1
        
        customers = []
        customer_time = 0.0
        if include_customers:
            customers, customer_time = results[idx]
        
        return {
            'items': items,
            'analytics': analytics,
            'customers': customers,
            'timings': {
                'items': item_time,
                'analytics': analytics_time,
                'customers': customer_time,
                'total_parallel': max(item_time, analytics_time, customer_time)
            }
        }

