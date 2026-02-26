---
title: Optimizing SQL Queries for Performance
tags: sql,database,performance
category: database
concepts: sql,query,index,explain,performance,join
---

## Reading EXPLAIN Plans and Index Strategies

The first step in optimizing a slow query is understanding what the database is actually doing. `EXPLAIN ANALYZE` (PostgreSQL) or `EXPLAIN QUERY PLAN` (SQLite) shows the execution plan: which indexes are used, how tables are scanned, and where time is spent.

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) AS order_count
FROM users u
JOIN orders o ON o.user_id = u.id
WHERE u.created_at > '2024-01-01'
GROUP BY u.id, u.name
ORDER BY order_count DESC
LIMIT 10;
```

Look for sequential scans on large tables. A sequential scan on a 10-row lookup table is fine; on a million-row table filtered by a WHERE clause, it means a missing index. Create indexes on columns that appear in WHERE, JOIN ON, and ORDER BY clauses. Composite indexes matter: an index on `(user_id, created_at)` serves queries filtering on both columns, but an index on `(created_at, user_id)` only helps if `created_at` is the leading filter.

Partial indexes reduce index size when you only query a subset of rows. In PostgreSQL: `CREATE INDEX idx_active_users ON users (email) WHERE active = true`. This index is smaller and faster than a full index on `email` because it excludes inactive users entirely.

Covering indexes include all columns a query needs, letting the database answer the query from the index alone without touching the table heap. Add `INCLUDE (name, email)` to an index in PostgreSQL when you frequently select those columns alongside indexed filter columns.

For general guidance on structuring database-heavy applications, see [rest-api-design](./rest-api-design.md).

## Join Optimization and the N+1 Problem

Join order affects performance. Most query planners choose the optimal join order automatically, but hints or restructuring can help when the planner's statistics are stale. Run `ANALYZE` periodically to refresh table statistics so the planner makes informed choices.

The N+1 query problem is the most common performance issue in applications using ORMs. Loading a list of users, then issuing a separate query per user to fetch their orders, produces N+1 round trips. The fix is a single JOIN or a subquery:

```sql
-- Instead of N+1 queries:
-- SELECT * FROM users;
-- SELECT * FROM orders WHERE user_id = 1;
-- SELECT * FROM orders WHERE user_id = 2; ...

-- Use a single join:
SELECT u.id, u.name, o.id AS order_id, o.total
FROM users u
LEFT JOIN orders o ON o.user_id = u.id
WHERE u.active = true;
```

ORMs provide eager loading mechanisms (`select_related` in Django, `joinedload` in SQLAlchemy, `include` in Prisma) that generate this join automatically. Enable query logging during development to catch N+1 patterns before they reach production. The [SQLAlchemy performance documentation](https://docs.sqlalchemy.org/en/20/faq/performance.html) covers detection strategies in detail.

Hash joins perform well when joining two large tables without useful indexes. Nested loop joins are efficient when the inner table has an index on the join column and the outer table is small. Merge joins work best when both inputs are already sorted on the join key. Understanding which join strategy the planner chose (visible in EXPLAIN output) helps you decide whether to add an index or restructure the query.

## Query Caching and Practical Tuning

Query result caching at the application layer avoids hitting the database for repeated reads. Cache the result set with a key derived from the query and parameters, and invalidate on writes to the underlying tables. TTL-based invalidation is simpler to implement than event-driven invalidation but tolerates stale reads.

```python
cache_key = f"users:active:page:{page}"
result = cache.get(cache_key)
if result is None:
    result = db.execute("SELECT ... LIMIT 20 OFFSET %s", (page * 20,))
    cache.set(cache_key, result, ttl=300)
```

Materialized views serve a similar purpose at the database level. PostgreSQL's `CREATE MATERIALIZED VIEW` precomputes expensive aggregations; refresh it on a schedule or trigger. The tradeoff is storage space and refresh latency versus query speed.

Connection pooling is orthogonal to query optimization but frequently surfaces during performance investigations. Each database connection consumes memory on the server. Use a pool (PgBouncer, SQLAlchemy's pool, HikariCP) to bound the connection count and reuse connections across requests. A pool sized to 2-3x the CPU core count of the database server is a reasonable starting point. See [debugging-memory-leaks](./debugging-memory-leaks.md) for diagnosing resource exhaustion caused by connection leaks.
