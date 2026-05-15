"""
VozFlix Recommendation System - Complete Deployment Guide
Production setup, monitoring, and operations
"""

# ==============================================================================
# COMPLETE DEPLOYMENT GUIDE
# ==============================================================================

## Step 1: Pre-Deployment Environment Setup

### 1.1 Install All Dependencies
```bash
cd fastapi-backend

# Install Python packages
pip install -r requirements.txt
pip install apscheduler  # Critical for background jobs

# Verify installation
python -c "import fastapi, motor, apscheduler; print('✓ All dependencies installed')"
```

### 1.2 Configure Environment Variables
Create `.env` file in `fastapi-backend/`:

```env
# MongoDB (Atlas or local)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
# OR for local:
# MONGODB_URI=mongodb://localhost:27017

# TMDB API
TMDB_API_KEY=your_tmdb_api_key_here

# JWT Security
JWT_SECRET=your_long_random_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# CORS (frontend URL)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,https://yourdomain.com

# Recommendation System
RECOMMENDATION_SYSTEM_ENABLED=true
```

### 1.3 Verify MongoDB Connectivity
```bash
# Test connection
python -c "
import asyncio
from motor.motor_asyncio import AsyncClient
async def test():
    client = AsyncClient('mongodb://localhost:27017')
    db = client['movie_db']
    await db.command('ping')
    print('✓ MongoDB connected')
asyncio.run(test())
"
```

---

## Step 2: Initialize MongoDB Collections & Indexes

### 2.1 Auto-Create Collections (Recommended)
Collections will be created automatically on first API request. However, you can manually initialize:

```bash
python -c "
import asyncio
from app.database import connect_to_mongo, get_db
from app.services.recommendation_init import initialize_recommendation_system

async def init():
    await connect_to_mongo()
    db = get_db()
    await initialize_recommendation_system(db)
    print('✓ Collections and indexes created')

asyncio.run(init())
"
```

### 2.2 Verify Collections
```bash
python -c "
import asyncio
from app.database import get_db
async def check():
    db = get_db()
    collections = await db.list_collection_names()
    print('Collections:')
    for c in collections:
        if 'recommendation' in c or 'user' in c or 'movie' in c:
            count = await db[c].count_documents({})
            print(f'  {c}: {count} documents')
asyncio.run(check())
"
```

---

## Step 3: Initialize Feature Data (One-Time Setup)

### 3.1 Extract Movie Features (~2-3 minutes)
```bash
python -c "
import asyncio
from app.database import connect_to_mongo, get_db
from app.services.content_features_service import ContentFeaturesService

async def extract():
    await connect_to_mongo()
    db = get_db()
    service = ContentFeaturesService(db)
    result = await service.extract_all_movie_features()
    print(f'Extracted features for {result[\"processed\"]} movies')

asyncio.run(extract())
"
```

### 3.2 Compute User Vectors (~1-2 minutes for 1K users)
```bash
python -c "
import asyncio
from app.database import connect_to_mongo, get_db
from app.services.user_vectorization_service import UserVectorizationService

async def compute():
    await connect_to_mongo()
    db = get_db()
    service = UserVectorizationService(db)
    result = await service.compute_all_user_vectors()
    print(f'Computed vectors for {result[\"processed\"]} users')

asyncio.run(compute())
"
```

### 3.3 Calculate User Behavior Signals (~30-60 seconds)
```bash
python -c "
import asyncio
from app.database import connect_to_mongo, get_db
from app.services.user_behavior_service import UserBehaviorService

async def calculate():
    await connect_to_mongo()
    db = get_db()
    service = UserBehaviorService(db)
    result = await service.calculate_all_user_signals()
    print(f'Calculated signals for {result[\"processed\"]} users')

asyncio.run(calculate())
"
```

---

## Step 4: Start the FastAPI Application

### 4.1 Development Mode (Single Worker)
```bash
cd fastapi-backend
uvicorn app.main:app --reload --port 8000
```

### 4.2 Production Mode (Multiple Workers)
```bash
cd fastapi-backend
# Using Gunicorn with async workers
pip install gunicorn
gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --port 8000

# OR using uvicorn with multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 4.3 Docker Deployment (Optional)
Create `Dockerfile` in `fastapi-backend/`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install apscheduler gunicorn

COPY . .

CMD ["gunicorn", "app.main:app", "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000"]
```

Build and run:
```bash
docker build -t vozflix-backend .
docker run -e MONGODB_URI=mongodb://... -e TMDB_API_KEY=... -p 8000:8000 vozflix-backend
```

---

## Step 5: Verify Deployment

### 5.1 Test Core Endpoints
```bash
# Test trending (no auth required)
curl http://localhost:8000/api/recommendations/trending

# Test personalized (requires auth)
TOKEN="your_jwt_token_here"
curl -H "Authorization: Bearer $TOKEN" \
     -X POST http://localhost:8000/api/recommendations/personalized

# Test health check
curl http://localhost:8000/api/test
```

### 5.2 Monitor Initial Startup
Look for these log messages:
```
✓ Recommendation background jobs scheduled
✓ MongoDB connected
Starting Uvicorn server at 0.0.0.0:8000
```

### 5.3 Check APScheduler Jobs
Monitor logs for job execution:
```
[RecommendationJobs] Starting recompute_user_vectors...
[RecommendationJobs] User vector recomputation complete. Processed: 1234
[RecommendationJobs] Starting refresh_behavior_signals...
[RecommendationJobs] Behavior signal refresh complete. Processed: 345
```

---

## Step 6: Setup Monitoring & Logging

### 6.1 Configure Application Logging
Update `fastapi-backend/app/main.py`:
```python
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

### 6.2 Monitor Key Metrics
Query the metrics endpoint:
```bash
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:8000/api/recommendations/metrics?period=last_7_days
```

Expected response:
```json
{
  "click_through_rate": 0.08,
  "completion_rate": 0.45,
  "average_score": 0.72,
  "genre_diversity": 0.82,
  "cache_hit_rate": 0.87,
  "average_computation_time_ms": 145
}
```

### 6.3 Setup Error Alerts
Configure alerts for:
- Job execution failures (check logs for ERROR)
- High error rate (>1% in /api/recommendations/*)
- Low cache hit rate (<50%)
- High latency (>500ms for recommendations)

---

## Step 7: Production Checklist

### Pre-Production Testing
- [ ] All pytest tests passing: `pytest tests/test_recommendations.py -v`
- [ ] Load testing with 1000+ concurrent users
- [ ] Verify database backup strategy
- [ ] Test failover/recovery procedures
- [ ] Verify HTTPS enabled for all endpoints
- [ ] Verify CORS settings don't expose to all origins
- [ ] Test with production data sample

### Deployment Checklist
- [ ] .env file created with all required variables
- [ ] MongoDB collections initialized
- [ ] Feature data extracted for all movies
- [ ] User vectors computed for existing users
- [ ] Behavior signals calculated
- [ ] FastAPI started successfully
- [ ] All endpoints responding (health check passes)
- [ ] APScheduler jobs running
- [ ] Logging configured and working
- [ ] Monitoring/alerting setup complete

### Post-Deployment Validation
- [ ] Users can get personalized recommendations
- [ ] Cache is working (logs show "cache hit")
- [ ] Trending movies are accurate
- [ ] Similar movies feature works
- [ ] Metrics endpoint returns data
- [ ] Background jobs complete successfully
- [ ] No ERROR logs in first hour

---

## Step 8: Production Operations

### 8.1 Daily Checks
```bash
# Check logs for errors
tail -f app.log | grep ERROR

# Verify background jobs ran
tail -100 app.log | grep RecommendationJobs

# Check database size
python -c "
import asyncio
from app.database import get_db
async def check():
    db = get_db()
    stats = await db.command('dbStats')
    print(f'Database size: {stats[\"dataSize\"] / 1024 / 1024:.1f} MB')
asyncio.run(check())
"
```

### 8.2 Weekly Maintenance
- [ ] Review CTR metrics (target: 5-10%)
- [ ] Check completion rate (target: 40-50%)
- [ ] Verify job execution durations are consistent
- [ ] Review error logs and fix any issues
- [ ] Backup MongoDB database

### 8.3 Monthly Reviews
- [ ] A/B test algorithm weights
- [ ] Review user feedback on recommendations
- [ ] Analyze recommendation quality trends
- [ ] Update documentation if needed
- [ ] Plan any necessary optimizations

### 8.4 Quarterly Reviews
- [ ] Large-scale A/B testing
- [ ] Algorithm parameter optimization
- [ ] Performance profiling
- [ ] Capacity planning for growth
- [ ] Security audit

---

## Step 9: Scaling & Optimization

### 9.1 For 10K+ Movies
```python
# recommendation_config.py
CANDIDATE_POOL_SIZE = 2000  # Increase candidate pool
CONTENT_FILTERS['min_vote_count'] = 50  # Lower to include more movies

# Consider:
# - Use approximate nearest neighbors (ANNOY, Faiss)
# - Batch similarity computation
# - Distribute across multiple workers
```

### 9.2 For 10K+ Users
```python
# recommendation_config.py
# Keep user vector computation as is (parallelizable)
# Enable Redis caching for vectors:
REDIS_ENABLED = True
REDIS_URL = "redis://localhost:6379"

# Consider:
# - Incremental vector updates (vs nightly full recomputation)
# - Use approximate SVD for vector computation
# - Sharding by user_id
```

### 9.3 For High Traffic (1000+ RPS)
```
- Use load balancer (nginx, HAProxy)
- Multiple FastAPI workers (8-16)
- Connection pooling for MongoDB
- Redis caching for all responses
- CDN for static assets
- Database read replicas for metrics
```

---

## Step 10: Disaster Recovery

### 10.1 Database Backup
```bash
# MongoDB Atlas (automatic)
# In Atlas UI: Backup & Restore → Set backup frequency

# Or manual backup:
mongodump --uri "mongodb+srv://..." --out ./backup
mongorestore --uri "mongodb+srv://..." ./backup
```

### 10.2 Recovery Procedure
If database is lost:
```bash
# 1. Restore from backup
mongorestore --uri "mongodb+srv://..." ./backup

# 2. Re-extract features
python app/scripts/extract_features.py

# 3. Re-compute vectors
python app/scripts/compute_vectors.py

# 4. Verify data integrity
python -c "
import asyncio
from app.database import get_db
async def verify():
    db = get_db()
    movies_count = await db['movies'].count_documents({})
    features_count = await db['movie_features'].count_documents({})
    print(f'Movies: {movies_count}, Features: {features_count}')
asyncio.run(verify())
"
```

---

## Troubleshooting Guide

### Problem: "ModuleNotFoundError: No module named 'apscheduler'"
**Solution:**
```bash
pip install apscheduler
# Restart FastAPI
```

### Problem: "Recommendations are very slow (>1s)"
**Solutions:**
1. Check cache hit rate: `GET /api/recommendations/metrics`
2. Verify MongoDB indexes exist
3. Reduce CANDIDATE_POOL_SIZE temporarily
4. Check MongoDB connection pool size

### Problem: "Background jobs not running"
**Solutions:**
1. Verify apscheduler installed
2. Check logs for "[RecommendationJobs]"
3. Verify app.state.scheduler is set
4. Check system time (affects cron scheduling)

### Problem: "New users not getting recommendations"
**Solution:**
This is expected! New users see trending/popular until they rate 3+ movies.

### Problem: "Database growth is too fast"
**Solutions:**
1. Verify TTL indexes are working (recommendation_logs should auto-delete after 90 days)
2. Run cleanup job manually: `await jobs.cleanup_old_logs()`
3. Consider reducing RECOMMENDATION_CACHE_TTL

---

**Deployment Complete! ✅**

Your VozFlix recommendation system is now in production and ready to serve personalized recommendations to users!

For detailed technical documentation, see:
- PHASE_1_SUMMARY.md — Data foundation
- PHASE_2_SUMMARY.md — Feature services  
- PHASE_3_4_SUMMARY.md — Engine & API
- PHASE_5_SUMMARY.md — Jobs & testing
- RECOMMENDATION_QUICK_REFERENCE.md — Quick lookup
