# Recommender Plan — v2 (FP-Growth + GRU4Rec)

Thay thế hoàn toàn TF-IDF/cosine recommender hiện tại. **Chạy 1 lần cho demo, không schedule, không Docker, không Redis.**

## Quyết định kiến trúc

| Quyết định | Lý do |
|---|---|
| **Bỏ TF-IDF + history_recommendation_service hiện tại** | Plan mới đảm nhận cả hai vai trò |
| **2 thuật toán: FP-Growth + GRU4Rec** | Bỏ LightFM (Windows build khó). Bỏ rail "Top Picks for You" trên home |
| **Mỗi thuật toán train 2 model riêng: movies / series** | Khớp với UI tách trang movies / series, không cross-recommend |
| **Synthetic seed users (`scripts/seed_demo_users.py`)** | Catalog ~300 phim + ít user thật → cần seed deterministic để demo ổn định |
| **Artifact ra `data/recommender/{fpgrowth,gru4rec}/{movies,series}/`** | Giữ pattern thư mục gitignored hiện tại |
| **Privacy rule cũ (training không đọc watch_history) BỊ HỦY** | Cả 2 thuật toán mới bắt buộc dùng `watch_history`. Lưu ý rõ trong CLAUDE.md |

## Schema MongoDB liên quan (không đổi)

```
watch_history { user_id, content_type, tmdb_id, season_number, episode_number,
                progress_seconds, completed, last_watched_at, created_at }
watchlist_items { user_id, content_type, tmdb_id, status, is_favorite, ... }
movies / series { tmdb_id, title|name, overview, genres[], ... }
```

**Định nghĩa positive signal** (dùng nhất quán cho cả 2 model):

```python
POSITIVE = {"completed": True} OR {"progress_seconds": {"$gte": 1800}}  # 30 min
```

cộng thêm `watchlist_items.is_favorite == True` (giá trị tín hiệu cao nhất).

---

## Phase 1 — Cleanup

1. **Xóa**:
   - `fastapi-backend/scripts/train_recommender.py`
   - `fastapi-backend/data/recommender/movies/`, `fastapi-backend/data/recommender/series/`
   - Toàn bộ tests liên quan TF-IDF: `tests/test_recommendation_service.py`, `tests/test_recommendations.py`, `tests/test_history_recommendation_service.py`, `tests/test_history_recommendations.py`
   - `fastapi-backend/HISTORY_RECOMMENDER_PLAN.md` (gộp về file này)

2. **Refactor (giữ file, rỗng hóa nội dung)**:
   - `app/services/recommendation_service.py` → đón inference FP-Growth
   - `app/services/history_recommendation_service.py` → đón inference GRU4Rec
   - `app/routers/recommendations.py` → mở 2 endpoint mới (xem Phase 5)

3. **Frontend cleanup**:
   - Xóa `recommendationsApi.similar` và `recommendationsApi.forYou` cũ trong `src/js/api.js`, thay bằng `related` + `nextInSequence` (xem Phase 5).
   - Xóa rail "Movies For You" / "Shows For You" trên home / movies / series page (thuộc `library_service.get_home_rails` và `get_movie_rails` / `get_series_rails`). Giữ rail "Continue Watching" (không phụ thuộc recommender).
   - Rail "More Like This" trên `detail.html` được wire lại sang FP-Growth.

---

## Phase 2 — Seed data demo (`scripts/seed_demo_users.py`)

Script Python độc lập, chạy 1 lần, idempotent (xóa user demo cũ trước khi seed lại).

**Tham số mặc định:**
- `N_USERS = 40` (email pattern `demo_user_{i:03d}@vozflix.demo`)
- `WATCHES_PER_USER ∈ [15, 40]`
- `random.seed(42)` → re-run cho ra kết quả y hệt
- Email demo tag: `is_demo_seed = True` để dễ wipe lại

**Logic sinh:**

1. Phân user vào **5 persona** theo genre ưu tiên: `action_fan`, `drama_fan`, `scifi_fan`, `comedy_fan`, `mixed`.
2. Với mỗi user, sample `WATCHES_PER_USER` titles từ `movies` + `series` có overlap với persona genres (80%) + random (20%).
3. Sinh chuỗi xem theo thời gian: `last_watched_at` cách nhau 1-3 ngày, lùi từ `now()`.
4. 70% records có `completed=True`, 20% `progress_seconds ∈ [1800, 7200]` (positive nhưng chưa xong), 10% `progress_seconds < 1800` (negative — không tính).
5. ~30% user có thêm 2-5 `watchlist_items` với `is_favorite=True`.

**Output:** insert vào `watch_history` + `watchlist_items` thật, log số records.

**Wipe lệnh:**
```bash
.venv\Scripts\python scripts/seed_demo_users.py --wipe   # xóa user is_demo_seed=True
.venv\Scripts\python scripts/seed_demo_users.py          # seed lại
```

---

## Phase 3 — FP-Growth ("Vì bạn đã xem...")

### Library
Thêm vào `requirements.txt`: `mlxtend>=0.23.0`.

### Training script: `scripts/train_fpgrowth.py`

Mỗi `content_type ∈ {movie, series}` tách riêng:

1. Pull `watch_history` ở positive signal (xem định nghĩa trên), group by `user_id`:
   ```
   transactions = [
       [tmdb_id, tmdb_id, ...],   # user 1
       [tmdb_id, tmdb_id, ...],   # user 2
       ...
   ]
   ```
2. Lọc transaction có ≥ 2 items (FP-Growth cần co-occurrence).
3. Encode bằng `TransactionEncoder` của mlxtend.
4. Chạy `fpgrowth(min_support=0.05)` rồi `association_rules(metric="confidence", min_threshold=0.2)`.
5. Build lookup: `{antecedent_tmdb_id → [consequent_tmdb_id ordered by lift desc]}`. Khi antecedent có >1 item (bigram, trigram), chỉ lấy rules có `len(antecedent) == 1` để giữ lookup O(1).
6. Cap top-20 consequents / antecedent.

**Output:** `data/recommender/fpgrowth/{movies,series}/rules.json` + `metadata.json` (gồm `min_support`, `min_confidence`, `n_transactions`, `n_rules`, `trained_at`).

### Inference: `app/services/recommendation_service.py`

```python
def related_items(content_type: str, tmdb_id: int, top_n: int = 10) -> list[int]:
    """Lookup từ rules.json, lazy-load lần đầu, return [] nếu không có rule."""
```

- Lazy load `rules.json` vào dict ở module level (như TF-IDF cũ).
- `RecommenderNotTrained` khi thiếu artifact → router trả 503.
- **Cold-start cho item không nằm trong rule:** trả `[]`. Frontend đã có sẵn pattern hide rail khi list rỗng (xem `for-you` flow cũ) → tận dụng.

### Route
`GET /api/recommendations/related/{content_type}/{tmdb_id}?limit=10` — **public, không auth** (giống endpoint `similar` cũ).

---

## Phase 4 — GRU4Rec ("Tiếp nối đam mê")

### Library
Thêm vào `requirements.txt`: `torch>=2.2.0` (CPU wheel).

### Training script: `scripts/train_gru4rec.py`

Mỗi `content_type` train 1 model riêng:

1. **Build item vocab:** lấy tất cả `tmdb_id` distinct từ `watch_history` (chỉ content_type tương ứng) + filter qua `movies`/`series` để loại item đã hidden. `pad_idx=0`, item index từ 1.
2. **Build sequences:** group `watch_history` theo `user_id`, sort theo `last_watched_at` asc, lấy chỉ positive signals. Bỏ user có chuỗi < 3 (không đủ context + target).
3. **Tạo training pairs sliding-window:** với chuỗi `[i1, i2, i3, i4, i5]`, sinh các cặp:
   ```
   ([i1, i2], i3), ([i1, i2, i3], i4), ([i1, i2, i3, i4], i5)
   ```
   Pad đầu lên `MAX_SEQ_LEN = 20`.
4. **Model (mini GRU4Rec):**
   ```
   item_emb : nn.Embedding(n_items+1, 64, padding_idx=0)
   gru      : nn.GRU(64, 128, batch_first=True)
   head     : nn.Linear(128, n_items+1)
   ```
   Loss: `CrossEntropyLoss(ignore_index=0)` trên logits của step cuối.
5. **Training:** `Adam(lr=1e-3)`, batch 64, 20 epochs (CPU đủ với dataset ~40 user). Print train loss / epoch.

**Output:** `data/recommender/gru4rec/{movies,series}/`:
- `model.pt` (state_dict)
- `item_vocab.json` (`{tmdb_id: idx}` + reverse)
- `metadata.json` (`max_seq_len`, `embed_dim`, `hidden_dim`, `n_items`, `trained_at`)

### Inference: `app/services/history_recommendation_service.py`

```python
async def next_in_sequence(user_id: str, content_type: str, top_n: int = 10) -> list[int]:
    """Predict next-N items dựa trên 20 phim user vừa xem gần nhất."""
```

Flow:
1. Lazy load model + vocab cho `content_type` (cache module-level).
2. Query `watch_history` user theo positive signal, sort `last_watched_at` desc, `limit(MAX_SEQ_LEN)`, đảo lại thành asc.
3. Map qua `item_vocab`, drop OOV (item seed sau training).
4. **Cold start:** chuỗi < 3 item sau filter → trả `[]`.
5. Forward → softmax → mask các item user đã xem → topk → reverse map về `tmdb_id`.
6. Wrap toàn bộ inference trong `with torch.no_grad():` + `model.eval()`.

### Route
`GET /api/recommendations/next/{content_type}?limit=10` — **yêu cầu auth** (cần user_id).

**Caching:** dùng `cachetools.TTLCache(maxsize=256, ttl=600)` key=`(user_id, content_type, limit)`. Bypass cache khi user push `watch_history` mới? — không cần cho demo, 10 phút là đủ.

---

## Phase 5 — API + Frontend integration

### Backend (`app/routers/recommendations.py`)

```python
router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

@router.get("/related/{content_type}/{tmdb_id}")    # FP-Growth, public
async def related(...): ...

@router.get("/next/{content_type}")                 # GRU4Rec, auth required
async def next_in_sequence(..., current_user=Depends(get_current_user)): ...
```

Cả hai endpoint **hydrate đầy đủ doc** qua `library_service.get_movies_by_tmdb_ids` / `get_series_by_tmdb_ids` với `include_hidden=False`. Pattern giống endpoint cũ — giữ helper `_hydrate(content_type, ids)`.

### Frontend

**`src/js/api.js`:**

```js
export const recommendationsApi = {
    related: (contentType, tmdbId, limit = 10) =>
        apiFetch(`/api/recommendations/related/${contentType}/${tmdbId}?limit=${limit}`),
    nextInSequence: (contentType, limit = 10) =>
        apiFetch(`/api/recommendations/next/${contentType}?limit=${limit}`),
};
```

**Wiring UI:**
- `public/pages/detail.html` — rail "Vì bạn đã xem..." gọi `related(contentType, tmdbId)`. Hide rail nếu API trả `[]`.
- `public/pages/discover.html` (home) — rail mới "Tiếp nối đam mê" (chỉ hiện khi đã login) gọi `nextInSequence("movie")` ở home. Thêm 1 rail riêng cho `series` ở trang series.
- **Xóa**: rail "Movies For You" / "Shows For You" cũ.

### Tests

Viết lại 2 file test mỏng (đủ pass coverage gate 60%):
- `tests/test_fpgrowth_recommender.py` — feed transactions synthetic, build artifact tạm, assert lookup đúng + cold-start trả `[]` + 503 khi thiếu artifact.
- `tests/test_gru4rec_recommender.py` — train mini model (2-3 epoch, 5 items) trên dummy data trong fixture, assert predict shape + cold-start `[]` + 401 khi không auth.
- Tận dụng `tmp_path` cho artifact, monkeypatch `ARTIFACT_ROOT`.

---

## Thứ tự thực thi (one-shot demo)

```bash
cd fastapi-backend

# 0. Cài deps mới
.venv\Scripts\pip install -r requirements.txt    # mlxtend + torch

# 1. Đảm bảo movies/series đã seed
.venv\Scripts\python scripts/seed_tmdb.py        # đã có sẵn

# 2. Seed demo users + watch_history
.venv\Scripts\python scripts/seed_demo_users.py

# 3. Train 2 model x 2 content_type
.venv\Scripts\python scripts/train_fpgrowth.py
.venv\Scripts\python scripts/train_gru4rec.py

# 4. Run server
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

## Rủi ro còn lại

| Rủi ro | Mitigation |
|---|---|
| FP-Growth `min_support=0.05` quá khắt khe → ít rule | Giảm xuống `0.03` nếu `n_rules < 50` sau train. Log warning. |
| GRU4Rec overfit dataset 40 user | Đủ cho demo, kết quả không cần đẹp về accuracy. Nếu loss > 5.0 sau 20 epoch → tăng epoch hoặc giảm `embed_dim`. |
| `torch` install lâu | Wheel CPU-only, ~150MB. Document trong README. |
| User thật (không phải seed) cold-start GRU4Rec | Endpoint trả `[]` → frontend hide rail. OK cho demo. |
| Phá privacy rule cũ | Update CLAUDE.md ngay sau khi merge: training giờ đọc `watch_history`, artifact không còn regenerable từ TMDB-only. |
