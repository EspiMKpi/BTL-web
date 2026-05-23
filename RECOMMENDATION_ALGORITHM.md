# Recommendation Algorithms — VozFlix (branch `test/kaggle`)

Tài liệu chi tiết về thuật toán Machine Learning đang chạy trong recommender system của VozFlix trên branch **`test/kaggle`**.

Khác với các branch dùng FP-Growth / GRU4Rec, branch này dùng **content-based recommender cổ điển** (TF-IDF + cosine similarity, đúng kiểu Kaggle notebook), cộng với một lớp **per-user aggregation** dùng MRR-style rank decay + exponential recency decay để tạo personalized "Recommended For You". Không có model học sâu, không có matrix factorization, không có graph network.

| Thành phần | Endpoint | Use-case UI | Auth |
|---|---|---|---|
| **TF-IDF + cosine** (item-to-item) | `GET /api/recommendations/similar/{content_type}/{tmdb_id}` | Rail *"More Like This"* trên trang detail | Public |
| **Per-user seed aggregation** (wrapper trên TF-IDF) | `GET /api/recommendations/for-you/{content_type}` | Rail *"Recommended For You"* trên home | Required |

Cả 2 endpoint dùng chung **một artifact duy nhất** (TF-IDF matrix) — endpoint `/for-you` chỉ là một lớp aggregation trên TF-IDF neighbours, không train model riêng.

**Privacy rule** (in đậm trong source): training **không bao giờ đọc `user_ratings` hay `watch_history`**. Features hoàn toàn từ TMDB metadata (`overview + genre names`). Artifact có thể rebuild bất kỳ lúc nào không cần dữ liệu người dùng — đây là lý do branch giữ được privacy posture mà các branch FP-Growth/GRU4Rec đã hủy.

---

## Phần 1 — TF-IDF + Cosine Similarity (item-to-item)

### 1.1 Ý tưởng & bài toán

**TF-IDF** (*Term Frequency — Inverse Document Frequency*, Spärck Jones 1972) là kỹ thuật biểu diễn một document thành vector số dựa trên tần suất từ, đã được điều chỉnh để giảm trọng số của các từ phổ biến (the, a, of, ...) và tăng trọng số của các từ đặc trưng cho document đó.

**Cosine similarity** đo độ tương đồng giữa 2 vector bằng góc giữa chúng — không phụ thuộc độ dài vector, chỉ quan tâm hướng.

Kết hợp 2 kỹ thuật này lên metadata phim (overview + genre) ⇒ recommender content-based: "phim nào có mô tả + thể loại giống phim X nhất thì gợi ý".

Ưu / nhược:
- ✅ Không cần dữ liệu user → không có cold-start cho user mới, không có vấn đề privacy.
- ✅ Train nhanh (sklearn, vài giây cho ~300 phim), inference nhanh (1 sparse dot product).
- ✅ Reproducible 100%, dễ debug (xem vocab + trọng số trực tiếp).
- ❌ Không personalize theo lịch sử user — phim nào cũng ra cùng kết quả với mọi user.
- ❌ Không capture được tín hiệu collaborative ("ai xem A cũng xem B").
- ❌ Phụ thuộc chất lượng `overview` — phim thiếu mô tả hoặc mô tả generic sẽ recommend kém.

### 1.2 Định nghĩa toán học

#### TF-IDF

Với document `d` trong corpus `D`, term `t` trong vocab:

**Term frequency** — số lần `t` xuất hiện trong `d`:

$$\text{tf}(t, d) = \frac{\#\{t \in d\}}{|d|}$$

(sklearn dùng raw count thay vì normalize; normalize được làm sau ở bước L2 trên vector cuối.)

**Inverse document frequency** — đo mức độ "đặc trưng" của term:

$$\text{idf}(t, D) = \ln\left(\frac{1 + |D|}{1 + |\{d \in D : t \in d\}|}\right) + 1$$

(công thức sklearn smoothed; cộng 1 ở tử + mẫu để tránh div-by-zero và term xuất hiện ở mọi doc vẫn có idf > 0.)

**TF-IDF weight**:

$$\text{tfidf}(t, d, D) = \text{tf}(t, d) \cdot \text{idf}(t, D)$$

Sau khi tính xong, sklearn `TfidfVectorizer` mặc định L2-normalize từng row vector:

$$\mathbf{v}_d = \frac{[\text{tfidf}(t_1, d), \text{tfidf}(t_2, d), ..., \text{tfidf}(t_V, d)]}{\| \cdot \|_2}$$

⇒ `||v_d||_2 = 1` cho mọi `d`. Đây là tối quan trọng cho bước cosine sau.

#### Cosine similarity

Với 2 vector `u, v`:

$$\cos(\theta) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \cdot \|\mathbf{v}\|_2}$$

Vì TF-IDF row đã L2-normalize, mẫu số = 1, nên:

$$\text{sim}(d_1, d_2) = \mathbf{v}_{d_1} \cdot \mathbf{v}_{d_2}$$

⇒ chỉ cần 1 phép dot product. Trên sparse matrix `M ∈ R^{N×V}`, similarity của doc `i` với toàn bộ corpus:

$$\mathbf{s}_i = M_i \cdot M^T \in \mathbb{R}^N$$

`M_i` là row sparse (kích thước 1×V), `M^T` là V×N → kết quả 1×N. Không bao giờ materialize toàn bộ `N×N` similarity matrix; chỉ tính row cần thiết theo query.

#### Top-K selection (argpartition vs argsort)

Để lấy top-K từ vector `s ∈ R^N`:
- `argsort` toàn bộ: O(N log N).
- `argpartition(s, -K)`: O(N) — partition thành "K phần tử lớn nhất" (không sort trong) → sau đó chỉ sort K phần tử đó: O(K log K).

Với `N ≈ 300, K = 10` thì chênh lệch không đáng kể, nhưng code chọn đúng theo `if top_n >= len(sims): argsort else argpartition`.

### 1.3 Pipeline training (`scripts/train_recommender.py`)

| Bước pipeline | Hàm / Code | Dòng |
|---|---|---|
| Constants: `ARTIFACT_ROOT`, `KIND`, `MAX_FEATURES` | module-level | **41–43** |
| Per-content-type config | `@dataclass CorpusConfig` + `CONFIGS` list | **46–57** |
| Build "soup" (overview + genre names) | `build_soup(overview, genre_names)` | **60–67** |
| Đọc Mongo, filter `is_hidden`, projection | `load_corpus(cfg)` | **70–108** |
| Skip docs thiếu `tmdb_id` hoặc soup rỗng | `if tmdb_id is None / if not soup` | **90–99** |
| Fit `TfidfVectorizer(stop_words="english", max_features=25_000, dtype=float32)` | `fit_and_persist` | **117–122** |
| Persist vectorizer (`joblib.dump`) | line 126 | **126** |
| Persist sparse matrix (`scipy.sparse.save_npz`) | line 127 | **127** |
| Persist item_index.json (`{tmdb_ids, titles}`) | lines 128–131 | **128–131** |
| Persist metadata.json (`kind, content_type, n_items, vocab_size`) | lines 132–142 | **132–142** |
| Orchestrate per-content-type training | `train_one(cfg)` | **146–162** |
| Connect Mongo + loop configs | `main()` | **165–178** |

**Hyperparameters chính**:
- `MAX_FEATURES = 25_000` — vocab cap (line **43**).
- `stop_words = "english"` — sklearn loại bỏ ~318 stop word tiếng Anh.
- `dtype = np.float32` — giảm memory + tăng tốc cosine dot product.
- Không dùng `ngram_range` (mặc định = unigram). Không lowercase tường minh (sklearn auto lowercase).

**Artifact layout:**

```
fastapi-backend/data/recommender/
├── movies/
│   ├── vectorizer.joblib     # sklearn TfidfVectorizer (vocab + idf weights)
│   ├── tfidf_matrix.npz      # scipy.sparse CSR (N x V)
│   ├── item_index.json       { "tmdb_ids": [...], "titles": [...] }
│   └── metadata.json         { built_at, content_type, n_items, vocab_size, kind }
└── series/
    └── (same structure)
```

Sạch sẽ tách `movies/` vs `series/` — **không** cross-recommendation giữa movies ↔ series.

### 1.4 Pipeline inference (`app/services/recommendation_service.py`)

| Chức năng | Hàm / Code | Dòng |
|---|---|---|
| Constants: `ARTIFACT_ROOT`, `EXPECTED_KIND`, `SUBDIR_BY_TYPE` | module-level | **23–26** |
| Module-level cache (per content_type) | `_STATE: dict[str, dict]` | **28** |
| Custom exception khi thiếu artifact | `class RecommenderNotTrained(RuntimeError)` | **31–32** |
| Validate content_type | `_validate_content_type` | **35–40** |
| Lazy load artifact + metadata validation | `_load(content_type)` | **43–79** |
| Verify `kind == "tfidf_overview_genres_v1"` | dòng 53–58 | **53–58** |
| Load vectorizer + sparse matrix | `joblib.load` + `sparse.load_npz` | **65–66** |
| Chuyển sang CSR (row slicing O(1)) | `matrix = matrix.tocsr()` | **67** |
| Build `id_to_idx` map | dict comp | **70** |
| **Public API**: top-N tương tự | `similar_to(content_type, tmdb_id, top_n)` | **82–110** |
| Item cold-start (ID không có trong index) | `if idx is None: return []` | **94–96** |
| Query row × matrix.T (sparse dot product) | `sims = query.dot(matrix.T).toarray().ravel()` | **100** |
| Loại item chính nó | `sims[idx] = -1.0` | **101** |
| Top-K (argsort hoặc argpartition theo size) | `if top_n >= len(sims): argsort else argpartition` | **103–107** |
| Filter `sims[i] > 0` (loại item disjoint vocab) | line 110 | **110** |
| Drop cache (manual reload) | `reload(content_type=None)` | **113–123** |

**Inference complexity:**
- 1 sparse row × sparse matrix.T dot product: O(nnz_row × N) trong worst case. Với TF-IDF nhỏ (avg ~50 non-zero per row, N≈300), nhanh < 1ms trên CPU.
- argpartition top-K: O(N).
- ⇒ Total per request ≈ µs. Không cần TTL cache.

### 1.5 Router (`app/routers/recommendations.py`)

| Chức năng | Dòng |
|---|---|
| Helper hydrate ids → docs (filter hidden) | `_hydrate(content_type, ids)` | **19–28** |
| **Endpoint `/similar/{content_type}/{tmdb_id}`** | `@router.get("/similar/...")` | **31–58** |
| Validate path params (`pattern="^(movie\|series)$"`, `ge=1`) | dòng 33–35 | **33–35** |
| Gọi inference + map `RecommenderNotTrained` → HTTP 503 | dòng 47–54 | **47–54** |
| Empty list bypass hydration | `if not ids: return []` | **56** |

Endpoint **public, không cần auth** — không phụ thuộc `user_id`.

### 1.6 Hành vi cold-start

- **Item cold-start**: `tmdb_id` chưa có trong trained index (vd. được seed sau lần training cuối, hoặc bị hide khi train) → `similar_to` trả `[]` (dòng 94–96) → router trả `200 OK [...]` → frontend hide rail.
- **Disjoint vocab**: Phim toàn từ ngoài stop-word + vocab → mọi sim = 0, sau filter `sims[i] > 0` còn lại rỗng → `[]`.
- **Catalog drift**: Item bị hide giữa training và request vẫn trong matrix nhưng sẽ bị filter ở `_hydrate` (`include_hidden=False`).

### 1.7 Ví dụ tay (toy corpus)

Giả sử corpus = 4 phim, soup đã được lowercase + loại stop-word:

```
d_1: "space stars galaxy aliens"
d_2: "space stars galaxy planets"
d_3: "space ships orbit"
d_4: "cooking pasta italian"
```

Vocab `V = {space, stars, galaxy, aliens, planets, ships, orbit, cooking, pasta, italian}` (10 từ).

**TF**: count per row (chuẩn hóa hay không tùy sklearn — kết quả cuối L2-norm sẽ đồng nhất). VD `tf(space, d_1) = 1`, `tf(cooking, d_1) = 0`.

**IDF** (công thức smoothed, `|D| = 4`):
- `idf(space) = ln(5 / (3+1)) + 1 = ln(1.25) + 1 ≈ 1.223` (xuất hiện 3 docs).
- `idf(cooking) = ln(5 / (1+1)) + 1 = ln(2.5) + 1 ≈ 1.916` (xuất hiện 1 doc).

→ Từ ít gặp (cooking) có trọng số cao hơn từ phổ biến (space).

**TF-IDF row d_1** sau L2-norm (chỉ minh họa, không tính chính xác):

```
v_1 ≈ [0.4_space, 0.4_stars, 0.4_galaxy, 0.7_aliens, 0, 0, 0, 0, 0, 0]   (||v||=1)
```

**Cosine similarity** với query `d_1`:
- `sim(d_1, d_2) ≈ 0.4*0.4 + 0.4*0.4 + 0.4*0.4 + 0 + 0 + ... ≈ 0.48` (chia sẻ 3 token).
- `sim(d_1, d_3) ≈ 0.4 * sqrt(small)` (chỉ chia sẻ "space") ≈ 0.16.
- `sim(d_1, d_4) = 0` (disjoint).

Top-2 cho `d_1` ⇒ `[d_2, d_3]`. `d_4` bị loại vì sim = 0.

---

## Phần 2 — Per-User Aggregation ("Recommended For You")

### 2.1 Ý tưởng & bài toán

TF-IDF cho item-to-item nhưng không personalize. Lớp này tạo personalized recommendations bằng cách:

1. Thu thập "seed items" của user — phim user đã thể hiện thích (`completed`, watched ≥ 30 min, hoặc favorite).
2. Với mỗi seed, lấy top-N items tương tự qua TF-IDF.
3. **Aggregate** các neighbours từ tất cả seeds với:
   - **Recency decay** trên `seed_weight` (phim xem lâu rồi có trọng số thấp hơn).
   - **Rank decay** trên contribution (neighbour rank 1 đóng góp gấp 10× neighbour rank 10).
4. Loại item user đã xem hoặc đã wishlist (`seen set`).
5. Rank theo aggregated score, trả top-N.

Không train model riêng. Toàn bộ "personalize" làm runtime trên top của TF-IDF.

### 2.2 Định nghĩa toán học

#### Recency decay (exponential half-life)

Cho `t` = số ngày từ lần xem cuối tới hiện tại, `H` = half-life (60 ngày):

$$w_{\text{recency}}(t) = 2^{-t/H} = e^{-t \cdot \ln 2 / H}$$

Đặc tính:
- `t = 0` ⇒ `w = 1.0` (vừa xem xong, full weight).
- `t = H = 60 ngày` ⇒ `w = 0.5` (nửa trọng số).
- `t = 2H = 120 ngày` ⇒ `w = 0.25`.
- `t → ∞` ⇒ `w → 0`.

⇒ Phim xem 1 tháng trước có trọng số ~0.71, xem nửa năm trước ~0.18.

**Favorites không decay** — bookmark là "active assertion" của user, không gắn với timestamp xem ⇒ weight = 1.0 cố định.

#### Seed weight merge

Một item có thể vừa trong `watch_history` (vd. weight 0.7 sau decay) vừa trong `favorites` (weight 1.0). Code chọn **max**:

$$w_{\text{seed}}(i) = \max(w_{\text{history}}(i), w_{\text{favorite}}(i))$$

Không sum để tránh bias quá mạnh cho item có cả 2 tín hiệu.

#### Rank decay (MRR-style)

Mỗi seed `s` sinh ra danh sách `K` neighbours qua TF-IDF, theo thứ tự cosine sim desc:

$$N_s = [n_1, n_2, ..., n_K]$$

Contribution của neighbour ở rank `r` (0-indexed):

$$c(s, n_r) = \frac{w_{\text{seed}}(s)}{r + 1}$$

Đặt tên "MRR-style" vì giống công thức MRR (*Mean Reciprocal Rank*): `1/1, 1/2, 1/3, ...`. Đặc tính:
- Rank 0 (top neighbour): contribution = `w_seed` (full weight).
- Rank 9 (10th neighbour): contribution = `w_seed / 10` (10× nhỏ hơn).
- Rank 19 (cuối): contribution = `w_seed / 20` (20× nhỏ hơn).

⇒ Neighbour càng đầu càng đóng góp mạnh.

#### Aggregate score

Với candidate `c` (không thuộc seen set, không thuộc seed set):

$$\text{score}(c) = \sum_{s \in \text{seeds}} \mathbb{1}[c \in N_s] \cdot \frac{w_{\text{seed}}(s)}{\text{rank}_s(c) + 1}$$

Trong đó `rank_s(c)` = vị trí của `c` trong neighbour list của `s` (chỉ tính khi `c ∈ N_s`).

⇒ Item được nhiều seed cùng "vote" và đứng ở vị trí cao trong các neighbour list sẽ được rank cao.

Cuối cùng sort theo `score(c)` desc, lấy top-N.

### 2.3 Code mapping (`app/services/history_recommendation_service.py`)

| Chức năng | Hàm / Code | Dòng |
|---|---|---|
| Tunable: half-life recency | `RECENCY_HALF_LIFE_DAYS = 60.0` | **28** |
| Tunable: positive signal threshold | `MIN_PROGRESS_SECONDS = 1800` | **31** |
| Tunable: neighbours per seed | `NEIGHBOURS_PER_SEED = 20` | **33** |
| Tunable: cold-start cutoff | `MIN_SEEDS_FOR_RECS = 3` | **35** |
| Exponential recency decay | `_recency_decay(when, half_life_days)` | **38–47** |
| Naive datetime → UTC fallback | dòng 42–43 | **42–43** |
| Future date guard | `if days <= 0: return 1.0` | **45–46** |
| Build seeds (history + favorites) | `_build_seeds(db, user_id, content_type)` | **50–86** |
| Positive signal filter (`completed` OR `progress >= 1800`) | dòng 55–63 | **55–63** |
| Collapse multi-row per title (`$group _id: $tmdb_id`) | dòng 64–67 | **64–67** |
| Apply recency decay khi build seed | `weight = _recency_decay(row.get("last_watched_at"))` | **71** |
| Favorites = full weight, no decay | `if 1.0 > seeds.get(tmdb_id, 0.0): seeds[tmdb_id] = 1.0` | **83–84** |
| Build seen set (history ∪ watchlist) | `_build_seen_set(db, user_id, content_type)` | **89–107** |
| **Core aggregation** | `_aggregate_neighbours(content_type, seeds, seen)` | **110–129** |
| Mỗi seed lấy K neighbours | `recommendation_service.similar_to(content_type, seed_id, top_n=NEIGHBOURS_PER_SEED)` | **122–124** |
| Filter loại item seen + loại seed khác | `if neighbour_id in seen or neighbour_id in seeds: continue` | **126–127** |
| MRR-style aggregation | `scores[neighbour_id] += seed_weight / (rank + 1)` | **128** |
| **Public API**: `for_user(user_id, content_type, n=10)` | dòng 132–154 | **132–154** |
| Validate content_type | dòng 140–144 | **140–144** |
| Cold-start check (< 3 seeds → `[]`) | `if len(seeds) < MIN_SEEDS_FOR_RECS: return []` | **148–149** |
| Sort by score desc + take top n | `sorted(scored, key=lambda kv: -kv[1])` + slice | **153–154** |

**Complexity:** O(`|seeds|` × `K`) cho aggregation, K = 20. Với 1 user có 50 seed: 1000 dict ops + sort 1000 items. Sub-millisecond trên CPU.

**Không có TTL cache** — vì TF-IDF inference cũng đã rất nhanh; user xem xong → push history → request mới phải reflect ngay.

### 2.4 Router (`app/routers/recommendations.py`)

| Chức năng | Dòng |
|---|---|
| **Endpoint `/for-you/{content_type}`** | `@router.get("/for-you/...")` | **61–87** |
| Require auth (`current_user = Depends(get_current_user)`) | dòng 65 | **65** |
| Gọi `history_recommendation_service.for_user(...)` | dòng 74–77 | **74–77** |
| `RecommenderNotTrained` → HTTP 503 | dòng 78–83 | **78–83** |
| Cold-start (empty) → `[]` không hydrate | dòng 85–86 | **85–86** |
| Hydrate (filter hidden) | `await _hydrate(content_type, ids)` | **87** |

Endpoint **require auth** vì cần `current_user["_id"]` để query history + watchlist.

### 2.5 Hành vi cold-start & edge cases

- **User cold-start**: < 3 positive seed (history + favorites) → trả `[]` → frontend hide rail.
- **Bounced watches** (`progress_seconds < 1800` và không `completed`) → bị loại ở `$match` (dòng 59–62), không tính seed.
- **Item-trong-seed**: candidate trùng với 1 seed khác (vd. user xem `Inception`, gợi ý `Interstellar` xếp rank 1 — nhưng `Interstellar` cũng nằm trong seeds) → bị skip (dòng 126–127) để tránh recommend lại phim đã xem.
- **Item-trong-seen**: thuộc history hoặc watchlist (kể cả bounced/plan_to_watch) → bị skip → không recommend lại.
- **Seen set vs seed set**: 2 set khác nhau! `seeds` chỉ là positive-signal items, `seen` là **mọi** item user từng touch (kể cả bounced + chỉ thêm vào watchlist). Cả 2 đều dùng để filter candidate, nhưng:
  - `seeds` quyết định *từ đâu suy ra* recommendation.
  - `seen` quyết định *cái gì bị loại* khỏi output.
- **Catalog drift**: cùng cơ chế với endpoint similar — `_hydrate(include_hidden=False)` filter lần cuối.

### 2.6 Ví dụ tay (mini scenario)

User có:
- `watch_history`: Inception (completed, 30 ngày trước), Interstellar (completed, 60 ngày trước), Tenet (progress 2000s, 5 ngày trước), Memento (progress 500s, 2 ngày trước).
- `watchlist_items` favorite: Dunkirk.

**Bước 1 — Build seeds:**
- Inception: `_recency_decay(30) = 2^(-30/60) ≈ 0.707` → weight 0.707.
- Interstellar: `2^(-60/60) = 0.5` → weight 0.5.
- Tenet: progress 2000 ≥ 1800 → positive; `2^(-5/60) ≈ 0.943` → weight 0.943.
- Memento: progress 500 < 1800, không completed → bị loại.
- Dunkirk: favorite → weight 1.0 (không decay).

⇒ `seeds = {Inception: 0.707, Interstellar: 0.5, Tenet: 0.943, Dunkirk: 1.0}` (4 seed ≥ 3 → không cold-start).

**Bước 2 — Build seen set:** `{Inception, Interstellar, Tenet, Memento, Dunkirk}` + bất kỳ phim nào trong watchlist khác.

**Bước 3 — Aggregate neighbours:** giả sử TF-IDF trả về:
- `similar_to(Inception, 20)` → `[Interstellar, Tenet, Prestige, Memento, ...]`.
- `similar_to(Interstellar, 20)` → `[Inception, Gravity, Tenet, Prestige, ...]`.
- `similar_to(Tenet, 20)` → `[Inception, Interstellar, Prestige, Insomnia, ...]`.
- `similar_to(Dunkirk, 20)` → `[Saving Private Ryan, 1917, Atonement, ...]`.

Xét candidate `Prestige`:
- Từ seed Inception (rank 2, 0-indexed): `0.707 / 3 ≈ 0.236`.
- Từ seed Interstellar (rank 3): `0.5 / 4 = 0.125`.
- Từ seed Tenet (rank 2): `0.943 / 3 ≈ 0.314`.
- Tổng: `score(Prestige) ≈ 0.675`.

Xét candidate `Saving Private Ryan`:
- Chỉ từ seed Dunkirk (rank 0): `1.0 / 1 = 1.0`.
- Tổng: `score(SPR) = 1.0`.

Xét candidate `Gravity`:
- Chỉ từ seed Interstellar (rank 1): `0.5 / 2 = 0.25`.
- Tổng: `score(Gravity) = 0.25`.

`Interstellar`, `Inception`, `Tenet`, `Memento` đều bị loại (in seeds hoặc seen).

**Ranked output**: `[SPR (1.0), Prestige (0.675), ..., Gravity (0.25)]`.

Lưu ý: Dunkirk (favorite) overshadow các seed history vì weight 1.0 không decay → Saving Private Ryan có cơ hội rank cao hơn dù chỉ được 1 seed vote. Đây là tradeoff thiết kế: bookmark = strong signal.

---

## Phần 3 — Tests

| Test file | Cover | Class chính |
|---|---|---|
| `tests/test_recommendation_service.py` (138 dòng) | TF-IDF inference, top-K, content_type validation, lazy load, kind mismatch, reload | `TestSimilarTo` **L15**, `TestContentTypeValidation` **L56**, `TestLoad` **L70**, `TestReload` **L94**, `TestLoadedState` **L127** |
| `tests/test_recommendations.py` (143 dòng) | HTTP `/similar` route, validation, 503, hydration, hidden filter | `TestValidation` **L13**, `TestNotTrained` **L31**, `TestEmptyResults` **L39**, `TestHydration` **L52** |
| `tests/test_history_recommendation_service.py` (236 dòng) | Per-user aggregation, cold-start, recency, content_type isolation, propagation, limit | `TestColdStart` **L43**, `TestPositiveSignals` **L73**, `TestNegativeFilters` **L111**, `TestRecency` **L153**, `TestContentTypeIsolation` **L177**, `TestPropagation` **L201**, `TestLimit` **L224** |
| `tests/test_history_recommendations.py` (191 dòng) | HTTP `/for-you` route, auth, validation, 503, cold-start, hydration | `TestAuth` **L25**, `TestValidation` **L51**, `TestNotTrained` **L71**, `TestColdStart` **L85**, `TestHydration` **L115** |

Fixtures trong `tests/conftest.py`:
- `artifact_root` (tmp_path, monkeypatch `ARTIFACT_ROOT`, clear `_STATE`) — dòng **78–88**.
- `build_artifacts(artifact_root, content_type, items, *, kind=None)` — builder callable cho TF-IDF artifact set, dòng **90–124**. Items: `[(tmdb_id, title, soup), ...]`. Cho phép `kind=` để test kind mismatch.

Tests không validate "chất lượng" recommendation (cần real corpus); chỉ validate data layer + math + cold-start contract + status codes.

---

## Phần 4 — So sánh với các nhánh khác

Branch `test/kaggle` là phiên bản **đơn giản nhất, không cần dữ liệu user để train**. So với 2 branch khác:

| Tiêu chí | TF-IDF + Cosine (`test/kaggle`) | FP-Growth (branch khác) | GRU4Rec (branch khác) |
|---|---|---|---|
| Loại thuật toán | Content-based, sparse vector | Association rule mining | Sequential deep learning |
| Training input | TMDB metadata (`overview + genres`) | `watch_history` (transactions) | `watch_history` (sequences) |
| Cần dữ liệu user để train? | ❌ Không | ✅ Có (per-user transactions) | ✅ Có (per-user sequences) |
| Privacy posture | ✅ Strong (regenerable từ TMDB) | ❌ Không (cần watch_history) | ❌ Không (cần watch_history) |
| Personalized? | Half — qua `/for-you` aggregation runtime | ❌ Không (theo item) | ✅ Có (theo user_id) |
| Capture thứ tự xem | ❌ Không | ❌ Không | ✅ Có |
| Library | scikit-learn, scipy, joblib, numpy | mlxtend | PyTorch |
| Inference cost | sparse dot product (µs) | O(1) dict lookup | GRU forward + topk |
| Training cost | giây (sklearn fit) | phút (mlxtend) | phút (PyTorch CPU) |
| Artifact format | `.joblib` + `.npz` + `.json` | `.json` | `.pt` + `.json` |
| Endpoint similar/related | `/similar/{type}/{tmdb_id}` | `/related/{type}/{tmdb_id}` | — |
| Endpoint personalized | `/for-you/{type}` (auth) | — | `/next/{type}` (auth) |

⇒ `test/kaggle` ưu tiên đơn giản + privacy; FP-Growth/GRU4Rec ưu tiên capture collaborative signal nhưng phải đánh đổi privacy.

---

## Phần 5 — Pipeline triển khai

```bash
cd fastapi-backend

# 1. Cài deps (scikit-learn + scipy + joblib + numpy)
.venv\Scripts\pip install -r requirements.txt

# 2. Seed catalog từ TMDB (~300 phim)
.venv\Scripts\python scripts/seed_tmdb.py

# 3. Train TF-IDF (1 lần cho movies + 1 lần cho series)
.venv\Scripts\python scripts/train_recommender.py

# 4. Run server
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

Khác với branches FP-Growth/GRU4Rec: **không cần `seed_demo_users.py`** vì TF-IDF không đọc `watch_history` trong lúc train. Catalog từ TMDB là đủ.

Retrain khi:
- Catalog có thay đổi lớn (thêm/xóa nhiều phim).
- Admin toggle hidden hàng loạt (item đã hide vẫn còn trong artifact cũ — sẽ bị `_hydrate(include_hidden=False)` filter, nhưng vocab có thể stale).

---

## Phần 6 — Lưu ý privacy & operational

- **Privacy rule còn nguyên**: training chỉ đọc `movies` và `series` collections (TMDB-sourced fields: `overview, genres.name`). KHÔNG đọc `user_ratings`, `watch_history`, `watchlist_items`. Artifact có thể rebuild bất kỳ lúc nào không cần dữ liệu user.
- **Determinism**: `TfidfVectorizer` với cùng input + cùng version sklearn cho output identical. Không có random seed nào trong training pipeline.
- **Cache invalidation**: in-memory `_STATE` dict, drop qua `recommendation_service.reload(content_type)` hoặc restart process. Không có TTL cache cho `/for-you` (mỗi request đều query Mongo cho seeds + seen).
- **Per-worker state**: mỗi uvicorn worker load matrix 1 lần độc lập. Với 4 workers × matrix ~vài MB là chấp nhận được.
- **Endpoint `/for-you` có race với background task `POST /api/history/progress`**: history được persist qua BackgroundTasks → có một độ trễ ngắn giữa "user push progress" và "for-you reflect". Không cache nên độ trễ này là deterministic, ≤ 1 request cycle.
