## 🚀 PostgreSQL 16 Released

**Source:** [Official PostgreSQL Release Notes](https://www.postgresql.org/about/news/postgresql-16-released-2686/)  
**Hacker News Discussion:** [HN Thread](https://news.ycombinator.com/item?id=40629177)

### 📚 Summary:
PostgreSQL 16—the latest big release of the popular open-source SQL database—brings several significant improvements in performance, parallelism, and developer experience. New features include:

- ⚡️ **Parallel Query Enhancements:** More types of queries (like FULL and RIGHT JOINs) can run in parallel, speeding up analytical workloads.
- 📈 **Logical Replication Upgrades:** Non-superusers can create publications and subscriptions, and bidirectional replication becomes more robust.
- 🔐 **Security Improvements:** Better security defaults and fine-grained access control on large objects.
- 🛠️ **Developer Quality-of-Life Features:** Expanded SQL/JSON standards support and enhanced monitoring for vacuum and query activity.
- ♻️ **Performance Gains:** Smarter query planning and improved sorting algorithms, especially for workloads with many concurrent connections.

### 🤔 Why So Popular?
- PostgreSQL is widely deployed in startups and enterprise alike, making each release highly anticipated.
- Performance improvements have immediate and tangible impact for users.
- Enhanced replication and developer features directly address long-standing community requests.

### 💬 Community Highlights & Sentiment
- **Sentiment:** Overwhelmingly positive 😊. Users praised the continuous, practical improvements and backwards compatibility focus.
- **Key Points:**
  - Calls to test the new version on real-world workloads before upgrading 🚨
  - Discussions about migration strategies from older major versions 🛤️
  - Excitement for parallel query improvements in analytic and OLAP settings 📊
  - Comparison with features in paid or proprietary database solutions 🤺

### 🔗 Sources
- [Official PostgreSQL Announcement](https://www.postgresql.org/about/news/postgresql-16-released-2686/)
- [Hacker News Discussion](https://news.ycombinator.com/item?id=40629177)

### 📝 Usage Example
Here is how you can enable parallel queries for an existing database:

```sql
-- Enable parallelism in postgresql.conf or via SQL
SET max_parallel_workers_per_gather = 4;
```

Then, for a large query:

```sql
SELECT COUNT(*) FROM massive_table WHERE processed = true;
-- This query now uses multiple CPU cores under the hood!
```

For more see the [Release Notes](https://www.postgresql.org/docs/16/release-16.html).