# Recommendation Algorithms — VozFlix

Tài liệu chi tiết về 2 thuật toán Machine Learning đang chạy trong recommender system của VozFlix.
Cả 2 thuật toán hoạt động **độc lập**, phục vụ 2 use-case khác nhau, và đều được train **per content_type** (1 model cho `movies`, 1 model cho `series` — không cross-recommend).

| Thuật toán | Endpoint | Use-case UI | Auth |
|---|---|---|---|
| **FP-Growth** (Association Rule Mining) | `GET /api/recommendations/related/{content_type}/{tmdb_id}` | Rail *"Vì bạn đã xem..."* / *"More Like This"* trên trang detail | Public |
| **GRU4Rec** (Sequential Recurrent NN) | `GET /api/recommendations/next/{content_type}` | Rail *"Tiếp nối đam mê"* / *"Up Next"* trên home/movies/series | Required |

Cả 2 thuật toán đều coi `watch_history` là nguồn tín hiệu duy nhất, với cùng một định nghĩa **positive signal**:

```python
completed == True  OR  progress_seconds >= 1800   # 30 phút
```

Constant: `MIN_PROGRESS_SECONDS = 1800` (định nghĩa ở `train_fpgrowth.py:53`, `train_gru4rec.py:58`, `history_recommendation_service.py:45`). Drift 3 giá trị này = silent train/serve skew → **luôn keep in sync**.

---

## Phần 1 — FP-Growth: Association Rule Mining

### 1.1 Ý tưởng & bài toán

FP-Growth (Frequent Pattern Growth, Han et al. 2000) là thuật toán **mining frequent itemsets** từ một tập transactions. Mỗi transaction là một tập items. Mục tiêu: tìm các tập items xuất hiện cùng nhau "đủ thường xuyên" trong dataset.

Trong VozFlix, mỗi user = 1 transaction, mỗi item = 1 `tmdb_id` mà user đó đã xem ở positive signal. Từ đó suy ra association rules dạng `A → B` ("user xem A thì cũng có khả năng xem B"), rồi quy về 1 bảng lookup `antecedent → [consequents]` để inference O(1).

So với Apriori (thuật toán cùng họ), FP-Growth nhanh hơn vì:
- Chỉ scan dataset 2 lần (Apriori scan O(k) lần với k = độ dài itemset dài nhất).
- Dùng cấu trúc **FP-Tree** nén toàn bộ transactions vào 1 prefix-tree, recursive mining trên tree thay vì generate-and-test candidate.

Mặt khác, FP-Growth không model thứ tự xem — chỉ "có xem hay không". Đó là lý do ta cần GRU4Rec cho use-case "next item".

### 1.2 Định nghĩa toán học

Cho:
- Tập transactions `T = {T_1, T_2, ..., T_n}`, mỗi `T_i ⊆ I` với `I` = universe of items.
- Itemset `X ⊆ I`.

**Support** của itemset `X`:

$$\text{support}(X) = \frac{|\{T_i \in T : X \subseteq T_i\}|}{|T|}$$

Phần trăm transactions chứa toàn bộ `X`. Trong code: `min_support = 0.05` mặc định ⇒ itemset phải xuất hiện trong ≥ 5% user mới được giữ.

**Confidence** của rule `A → B` (với `A, B ⊆ I`, `A ∩ B = ∅`):

$$\text{confidence}(A \Rightarrow B) = \frac{\text{support}(A \cup B)}{\text{support}(A)} = P(B \mid A)$$

Xác suất user có `B` trong watch list, **với điều kiện** đã có `A`. Mặc định: `min_confidence = 0.2`.

**Lift** của rule `A → B`:

$$\text{lift}(A \Rightarrow B) = \frac{\text{confidence}(A \Rightarrow B)}{\text{support}(B)} = \frac{P(A \cap B)}{P(A) \cdot P(B)}$$

- `lift > 1`: A và B **co-occur nhiều hơn** so với nếu chúng độc lập → tín hiệu tốt.
- `lift = 1`: độc lập, rule vô nghĩa.
- `lift < 1`: negative correlation.

VozFlix **rank consequents theo lift desc** (không phải confidence) — vì confidence cao có thể chỉ là do `B` rất phổ biến (mọi user đều xem), trong khi lift loại bỏ baseline popularity và đo "mạnh hơn chance bao nhiêu".

### 1.3 FP-Tree & thuật toán mining (concept)

FP-Growth (chạy bên trong `mlxtend.frequent_patterns.fpgrowth`) gồm 2 bước:

**Bước 1 — Build FP-Tree:**
1. Scan transactions lần 1, đếm support của từng item đơn lẻ. Loại item có `support < min_support`.
2. Sort items còn lại theo support desc → "header table".
3. Scan transactions lần 2; với mỗi transaction, sort items theo thứ tự header, rồi insert thành 1 path trong cây. Các transactions chia sẻ prefix sẽ dùng chung node ⇒ cây nén lại đáng kể.

**Bước 2 — Mine recursive:**
Với mỗi item `i` trong header table (xét từ ít phổ biến nhất → phổ biến nhất):
1. Build **conditional pattern base**: tập các prefix paths kết thúc bằng `i`.
2. Build **conditional FP-Tree** từ pattern base đó.
3. Recursively mine conditional tree → ra frequent itemsets chứa `i`.
4. Output: tất cả itemsets `X` với `support(X) ≥ min_support`.

Từ frequent itemsets, `mlxtend.frequent_patterns.association_rules` enumerate mọi cách chia `X = A ∪ B` (A, B disjoint), tính confidence + lift, filter theo `min_confidence`.

### 1.4 Code mapping — Training (`scripts/train_fpgrowth.py`)

| Bước pipeline | Hàm | Dòng |
|---|---|---|
| Build transactions từ watch_history | `_build_transactions(db, content_type)` | **65–85** |
| Filter positive signal + group by user | `aggregate $match + $group` trong query trên | **67–79** |
| Drop transaction < 2 items | `if len(ids) >= 2` | **83–84** |
| One-hot encode bằng `TransactionEncoder` | `_mine_rules` setup | **94–96** |
| Run `fpgrowth` để mine frequent itemsets | `fpgrowth(df, min_support=support, use_colnames=True)` | **100** |
| Derive association rules | `association_rules(itemsets, metric="confidence", min_threshold=min_confidence)` | **104–106** |
| Giữ chỉ rule 1-item antecedent | `rules_df[rules_df["antecedents"].apply(lambda s: len(s) == 1)]` | **110** |
| Auto-halve `min_support` nếu < 10 rules | `while True` loop với floor `0.01` | **98–116** |
| Rank consequents theo lift desc, cap top-20 | `_to_lookup(rules_df)` | **119–139** |
| Dedupe consequents (max-lift instance) | `if lift > best.get(cons, -inf)` | **131–135** |
| Write `rules.json` + `metadata.json` | `_write_artifacts` | **142–174** |

**Tham số mặc định** (`train_fpgrowth.py:213–218`):
- `--min-support = 0.05` (sẽ auto-halve về `0.01` nếu mined < 10 rules).
- `--min-confidence = 0.2`.
- `TOP_K_CONSEQUENTS = 20` (cap mỗi antecedent).
- `MIN_RULES_TARGET = 10`, `MIN_SUPPORT_FLOOR = 0.01`.

**Artifact layout:**

```
fastapi-backend/data/recommender/fpgrowth/
├── movies/
│   ├── rules.json       { "550": [101, 102, 103, ...], ... }   # antecedent → consequents
│   └── metadata.json    { kind, content_type, min_support_used, n_transactions, ... }
└── series/
    └── (same structure)
```

`rules.json` được sort sẵn theo lift desc, mỗi antecedent capped 20 → inference chỉ là 1 dict lookup + slice top-N.

### 1.5 Code mapping — Inference (`app/services/recommendation_service.py`)

| Chức năng | Hàm | Dòng |
|---|---|---|
| Module state cache (per content_type) | `_STATE: dict[str, dict]` | **28** |
| Custom exception khi thiếu artifact | `RecommenderNotTrained` | **31–32** |
| Validate content_type | `_validate_content_type` | **35–40** |
| Lazy-load `rules.json` + `metadata.json` | `_load(content_type)` | **43–76** |
| Verify `kind == "fpgrowth_v1"` | check `metadata.get("kind") != EXPECTED_KIND` | **54–59** |
| Parse JSON string keys → int | `{int(k): [int(x) for x in v] ...}` | **68–70** |
| **Public API** — return ranked tmdb_ids | `related_items(content_type, tmdb_id, top_n)` | **79–95** |
| Drop cached state | `reload(content_type=None)` | **98–104** |

**Inference complexity:** O(1) lookup + O(top_n) slice. Không có matrix multiply, không model forward — đơn giản chỉ là tra bảng đã được train trước.

### 1.6 Code mapping — Router (`app/routers/recommendations.py`)

| Chức năng | Dòng |
|---|---|
| Endpoint definition `@router.get("/related/{content_type}/{tmdb_id}")` | **32–37** |
| Gọi inference + map `RecommenderNotTrained` → HTTP 503 | **48–55** |
| Hydrate tmdb_ids thành Mongo docs (`_hydrate`) | **57–59** + **20–29** |
| Filter `include_hidden=False` | trong `_hydrate` qua `get_movies_by_tmdb_ids` | **25** / **27** |

Endpoint **public, không cần auth** — vì không cần `user_id`, chỉ cần `tmdb_id` của item đang xem.

### 1.7 Hành vi cold-start

- **Item cold-start**: `tmdb_id` chưa từng appear làm antecedent trong rule nào (chưa co-watch với ai đủ ngưỡng) → `related_items` trả `[]` → router trả `200 OK` với body `[]` → frontend hide rail.
- **Catalog drift**: Item được hide sau training vẫn ở trong `rules.json` nhưng sẽ bị filter ở `_hydrate` (`include_hidden=False`) → silently dropped.

### 1.8 Ví dụ tay (toy data)

Giả sử có 4 user, content_type = movie:

```
T_1 = {Inception, Interstellar, Tenet}
T_2 = {Inception, Interstellar}
T_3 = {Inception, Tenet, Memento}
T_4 = {Interstellar, Tenet, Memento}
```

Với `min_support = 0.5`:

| Itemset | Count | Support |
|---|---|---|
| {Inception} | 3 | 0.75 ✓ |
| {Interstellar} | 3 | 0.75 ✓ |
| {Tenet} | 3 | 0.75 ✓ |
| {Memento} | 2 | 0.50 ✓ |
| {Inception, Interstellar} | 2 | 0.50 ✓ |
| {Inception, Tenet} | 2 | 0.50 ✓ |
| {Interstellar, Tenet} | 2 | 0.50 ✓ |
| {Tenet, Memento} | 2 | 0.50 ✓ |

Rule `Inception → Interstellar`:
- `confidence = support({Inception, Interstellar}) / support({Inception}) = 0.50 / 0.75 ≈ 0.667`
- `lift = 0.667 / 0.75 ≈ 0.889` (lift < 1, không gợi ý)

Rule `Memento → Tenet`:
- `confidence = 0.50 / 0.50 = 1.0`
- `lift = 1.0 / 0.75 ≈ 1.333` (lift > 1 → rule mạnh, gợi ý)

⇒ `rules.json["memento_id"] = [tenet_id, ...]`.

---

## Phần 2 — GRU4Rec: Sequential Recommendation với GRU

### 2.1 Ý tưởng & bài toán

GRU4Rec (Hidasi et al., 2016, *"Session-based Recommendations with Recurrent Neural Networks"*) là kiến trúc dùng **Gated Recurrent Unit (GRU)** để học representation của một session/sequence các item, và **predict item tiếp theo**.

VozFlix dùng phiên bản đơn giản hóa:
- Mỗi user = 1 sequence chronological các tmdb_id (positive signal, dedupe per (user, tmdb_id) giữ lần xem gần nhất).
- Train kiểu **next-item prediction**: cho context `[i_1, i_2, ..., i_{t-1}]`, predict `i_t`.
- Inference: lấy 20 item gần nhất của user, feed model, top-K logits = recommendations.

Khác với FP-Growth (pairwise, không thứ tự), GRU4Rec capture **trajectory**: user xem (Batman Begins → Dark Knight) khác với user xem (Dark Knight → Batman Begins) về mặt context state.

### 2.2 Kiến trúc model

```
input:   seq = [pad, pad, ..., i_{t-K}, ..., i_{t-2}, i_{t-1}]   (B × T, int64, 0 = pad)
   │
   ▼
Embedding (V × E, padding_idx=0)          → emb: (B, T, E)
   │
   ▼
GRU (E → H, single layer, batch_first)     → out: (B, T, H)
   │
   ▼
take last timestep: out[:, -1, :]          → last: (B, H)
   │
   ▼
Linear (H → V)                             → logits: (B, V)
   │
   ▼
mask logits[:, 0] = -inf  (không predict pad)
   │
   ▼
output: logits over vocab, argmax = next item
```

Hyperparameters (`scripts/train_gru4rec.py:49–55`):

| Tên | Giá trị | Vai trò |
|---|---|---|
| `EMBED_DIM` | `64` | Chiều embedding mỗi item |
| `HIDDEN_DIM` | `128` | Chiều hidden state GRU |
| `MAX_SEQ_LEN` | `20` | Độ dài tối đa của context (left-padded) |
| `BATCH_SIZE` | `64` | |
| `LR` | `1e-3` | Adam learning rate |
| `N_EPOCHS` | `20` | |
| `SEED` | `42` | Reproducibility |

`vocab_size = số tmdb_id unique + 1` (vì index 0 reserved cho pad).

### 2.3 Định nghĩa toán học

**Embedding lookup:**

$$\mathbf{e}_t = E[i_t] \in \mathbb{R}^E$$

với `E ∈ R^{V×E}` là embedding matrix (`item_emb`).

**GRU recurrent unit** (Cho et al., 2014):

$$
\begin{aligned}
z_t &= \sigma(W_z \mathbf{e}_t + U_z h_{t-1} + b_z) \quad &\text{(update gate)} \\
r_t &= \sigma(W_r \mathbf{e}_t + U_r h_{t-1} + b_r) \quad &\text{(reset gate)} \\
\tilde{h}_t &= \tanh(W_h \mathbf{e}_t + U_h (r_t \odot h_{t-1}) + b_h) \\
h_t &= (1 - z_t) \odot h_{t-1} + z_t \odot \tilde{h}_t
\end{aligned}
$$

trong đó:
- `σ` = sigmoid, `⊙` = element-wise product.
- `z_t` quyết định bao nhiêu thông tin cũ giữ lại, bao nhiêu thông tin mới ghi đè.
- `r_t` quyết định bao nhiêu hidden state cũ tham gia vào tính `\tilde{h}_t`.
- `h_t ∈ R^H` là hidden state mới.

**Output layer** (linear projection sang vocab):

$$\mathbf{o} = W_o h_T + b_o \in \mathbb{R}^V$$

với `T` = timestep cuối (sau khi đã process toàn bộ sequence).

**Predictive distribution** (sau khi mask pad + seen items):

$$P(i_{T+1} = v \mid i_1, ..., i_T) = \text{softmax}(\mathbf{o})_v = \frac{\exp(o_v)}{\sum_{v'} \exp(o_{v'})}$$

(Inference không cần softmax tường minh — chỉ cần `topk(logits)` vì softmax monotonic.)

**Loss function** (training):

$$\mathcal{L} = -\frac{1}{N} \sum_{(\mathbf{c}, t) \in \mathcal{D}} \log P(t \mid \mathbf{c}) = -\frac{1}{N} \sum \log \text{softmax}(\mathbf{o}_\mathbf{c})_t$$

= **cross-entropy** giữa predicted distribution và target item (1-hot). PyTorch: `nn.CrossEntropyLoss()`.

**Optimizer:** Adam với learning rate `1e-3`. Adam update:

$$
\begin{aligned}
m_t &= \beta_1 m_{t-1} + (1-\beta_1) g_t \\
v_t &= \beta_2 v_{t-1} + (1-\beta_2) g_t^2 \\
\hat{m}_t &= m_t / (1 - \beta_1^t), \quad \hat{v}_t = v_t / (1 - \beta_2^t) \\
\theta_t &= \theta_{t-1} - \eta \cdot \hat{m}_t / (\sqrt{\hat{v}_t} + \epsilon)
\end{aligned}
$$

(`β_1 = 0.9`, `β_2 = 0.999`, `ε = 1e-8` mặc định.)

### 2.4 Code mapping — Model class (`app/services/history_recommendation_service.py`)

| Layer / chức năng | Hàm/Code | Dòng |
|---|---|---|
| Class definition | `class GRU4RecModel(nn.Module)` | **55–75** |
| Embedding layer | `nn.Embedding(vocab_size, embed_dim, padding_idx=0)` | **64** |
| GRU layer | `nn.GRU(embed_dim, hidden_dim, batch_first=True)` | **65** |
| Output projection | `nn.Linear(hidden_dim, vocab_size)` | **66** |
| Forward — embed + GRU | `emb = self.item_emb(seq); out, _ = self.gru(emb)` | **70–71** |
| Lấy timestep cuối | `last = out[:, -1, :]` | **72** |
| Logits + mask pad | `logits[:, 0] = float("-inf")` | **73–74** |

Lưu ý: class này được **share** giữa training (`scripts/train_gru4rec.py:43` import) và inference, nên kiến trúc đồng bộ tự động.

### 2.5 Code mapping — Training (`scripts/train_gru4rec.py`)

| Bước pipeline | Hàm | Dòng |
|---|---|---|
| Dataset wrapper | `class SequenceDataset(Dataset)` | **67–83** |
| Fetch + dedupe user sequences | `_fetch_user_sequences` | **86–125** |
| Group by user, sort chronological | `aggregate $sort {last_watched_at: 1}` | **109–116** |
| Filter user sequence < 3 | `if len(seq) >= MIN_USER_SEQUENCE_LEN` | **123–124** |
| Build vocab (index 0 = pad, items từ 1) | `_build_vocab(sequences)` | **128–140** |
| Sliding-window (context, target) pairs | `_build_training_pairs` | **143–169** |
| Left-pad context tới `max_seq_len` | `[0] * (max_seq_len - len(ctx)) + ctx` | **158** |
| Training loop | `_train(model, loader, n_epochs, lr, device)` | **174–202** |
| Adam optimizer | `torch.optim.Adam(model.parameters(), lr=lr)` | **182** |
| Cross-entropy loss | `nn.CrossEntropyLoss()` | **183** |
| Forward + backward step | `logits = model(ctx); loss = loss_fn(logits, tgt); loss.backward(); optim.step()` | **192–195** |
| Write artifacts | `_write_artifacts` | **205–245** |
| Save `state_dict` | `torch.save(model.state_dict(), subdir / "model.pt")` | **221** |
| Save vocab JSON | `(subdir / "item_vocab.json").write_text(...)` | **222–228** |
| Save metadata + epoch losses | `(subdir / "metadata.json").write_text(...)` | **229–244** |

**Sliding window generation** (dòng **152–160**): cho sequence `[i_1, i_2, i_3, i_4, i_5]` và `max_seq_len = 4`, ta sinh các cặp:

```
(context=[0, 0, 0, i_1],     target=i_2)
(context=[0, 0, i_1, i_2],   target=i_3)
(context=[0, i_1, i_2, i_3], target=i_4)
(context=[i_1, i_2, i_3, i_4], target=i_5)
```

**Artifact layout:**

```
fastapi-backend/data/recommender/gru4rec/
├── movies/
│   ├── model.pt           # torch state_dict (Embedding + GRU + Linear weights)
│   ├── item_vocab.json    { "tmdb_to_idx": {...}, "idx_to_tmdb": [0, tmdb_id, ...] }
│   └── metadata.json      { kind, content_type, embed_dim, hidden_dim, max_seq_len, n_items, epoch_losses, ... }
└── series/
    └── (same structure)
```

### 2.6 Code mapping — Inference (`app/services/history_recommendation_service.py`)

| Chức năng | Hàm | Dòng |
|---|---|---|
| Constant: positive signal threshold | `MIN_PROGRESS_SECONDS = 1800` | **45** |
| Constant: cold-start cutoff | `MIN_SEQUENCE_LEN = 3` | **47** |
| TTL prediction cache (10 phút) | `_predict_cache = TTLCache(maxsize=512, ttl=600)` | **52** |
| Lazy load model + vocab + meta | `_load(content_type)` | **86–131** |
| Load state_dict | `torch.load(model_path, map_location="cpu", weights_only=True)` | **120** |
| Set eval mode | `model.eval()` | **122** |
| Fetch recent positive items (asc) | `_fetch_recent_positive_items` | **134–162** |
| Positive signal filter | `$match {$or: [{completed: True}, {progress_seconds: {$gte: MIN_PROGRESS_SECONDS}}]}` | **143–148** |
| Dedupe per tmdb_id, lấy latest | `$group {_id: $tmdb_id, last_watched_at: {$first: ...}}` | **151–154** |
| Reverse desc → asc cho GRU | `rows.reverse()` | **161** |
| Forward pass + topk + mask seen | `_predict(state, seq_idx, seen_idx, top_n)` | **165–197** |
| Truncate sequence > max_seq_len | `seq_idx = seq_idx[-max_len:]` | **173–174** |
| Left-pad context | `padded = [0] * (max_len - len(seq_idx)) + seq_idx` | **176** |
| No-grad forward | `with torch.no_grad(): logits = state["model"](seq)` | **179–180** |
| Mask seen items | `for idx in seen_idx: logits[idx] = float("-inf")` | **184–186** |
| Topk + map idx → tmdb_id | `torch.topk(logits, k).indices.tolist()` | **189–197** |
| **Public API** | `async def next_in_sequence(user_id, content_type, n=10)` | **200–235** |
| Cache key + lookup | `cache_key = (user_id, content_type, n); _predict_cache.get(cache_key)` | **212–215** |
| Cold-start check | `if len(seq_idx) < MIN_SEQUENCE_LEN: return []` | **228–230** |
| Cache write | `_predict_cache[cache_key] = result` | **234** |

**Inference complexity:** 1 forward pass GRU O(T × H × E) + 1 topk O(V log K). Với `T=20, H=128, E=64, V≈300`: ~µs trên CPU. TTL cache 10 phút che các request lặp lại trong cùng phiên người dùng.

### 2.7 Code mapping — Router (`app/routers/recommendations.py`)

| Chức năng | Dòng |
|---|---|
| Endpoint `@router.get("/next/{content_type}")` | **62–66** |
| Require auth (`current_user = Depends(get_current_user)`) | **66** |
| Gọi `next_in_sequence(current_user["_id"], ...)` | **74–76** |
| `RecommenderNotTrained` → HTTP 503 | **77–82** |
| Hydrate ids → Mongo docs (filter hidden) | **84–86** + **20–29** |

### 2.8 Hành vi cold-start & robustness

- **User cold-start**: < 3 positive item nằm trong trained vocab → trả `[]` → frontend hide rail.
- **OOV item**: tmdb_id user vừa xem nhưng chưa có trong vocab (vd. catalog mở rộng sau training) → bị drop ở dòng **227** (`if t in tmdb_to_idx`). Nếu sau khi drop còn < 3 → cold start.
- **Already-watched mask**: dòng **184–186** set logits của mọi item user đã xem = `-inf` → không bao giờ recommend lại.
- **Stale artifact**: training cũ + catalog mới → vocab outdated nhưng không crash, chỉ là recommendation quality giảm cho item mới. Re-run train script sau khi seed nhiều content mới.
- **Catalog drift**: tmdb_id predicted bị hide hoặc xóa giữa training và request → bị filter ở `_hydrate` (`include_hidden=False`).

### 2.9 Ví dụ tay (toy forward pass)

Giả sử `V = 6` (0=pad, 1..5 = 5 phim), `E = 2`, `H = 3`, `max_seq_len = 4`.

User vừa xem `[i_2, i_4]` (theo thứ tự thời gian) ⇒ left-padded: `[0, 0, 2, 4]`.

1. Embed: lookup `E[0]=[0,0]` (pad), `E[2]=[0.1, 0.5]`, `E[4]=[0.3, -0.2]`. → `emb` shape `(1, 4, 2)`.
2. GRU process 4 timestep, hidden state cuối cùng `h_4 ∈ R^3` capture toàn bộ context.
3. Linear projection: `o = W_o · h_4 + b_o ∈ R^6`. Giả sử `o = [-inf, 2.1, 0.8, -0.5, 1.2, 1.7]`.
   - Index 0 đã bị mask thành `-inf` (pad).
4. Mask seen: `o[2] = -inf` (đã xem i_2), `o[4] = -inf` (đã xem i_4). → `o = [-inf, 2.1, -inf, -0.5, -inf, 1.7]`.
5. Topk(o, k=2) → indices `[1, 5]` → tmdb_ids `[idx_to_tmdb[1], idx_to_tmdb[5]]`.

⇒ recommendation = `[i_1, i_5]`.

---

## Phần 3 — Tests

| Test file | Cover | Dòng đáng chú ý |
|---|---|---|
| `tests/test_fpgrowth_recommender.py` | Inference (build rules.json tay), HTTP route, cold-start, hidden filter, lazy-load cache | `TestRelatedItems` **19–73**, `TestRelatedRoute` **78–150** |
| `tests/test_gru4rec_recommender.py` | Inference với model random-init, masking, OOV drop, cold-start, TTL cache reuse, HTTP route | `TestNextInSequence` **42–189**, `TestNextRoute` **194–248** |

Tests không validate quality của prediction (cần real training data); chỉ validate IO/data layer + masking + cold-start contract + route status codes.

Fixtures `build_fpgrowth_artifacts` / `build_gru4rec_artifacts` + `fpgrowth_artifact_root` / `gru4rec_artifact_root` ở `tests/conftest.py` build artifact trong tmp dir và redirect `ARTIFACT_ROOT`.

---

## Phần 4 — Tóm tắt so sánh

| Tiêu chí | FP-Growth | GRU4Rec |
|---|---|---|
| Loại thuật toán | Association rule mining | Sequential deep learning |
| Input | Tập transactions (unordered sets per user) | Chuỗi thời gian per user |
| Output | `antecedent → [consequent]` lookup table | Softmax over vocab |
| Capture thứ tự xem | ❌ Không | ✅ Có |
| Personalized? | ❌ Không (theo item, không theo user) | ✅ Có (theo user_id) |
| Cold-start item | Item chưa appear → `[]` | OOV drop, ≥ 3 in-vocab mới predict |
| Cold-start user | N/A (không dùng user_id) | < 3 positive in-vocab → `[]` |
| Inference cost | O(1) dict lookup | 1 GRU forward + topk |
| Training cost | Phút (mlxtend, không GPU) | Phút (PyTorch CPU, ~20 epoch, 40 user) |
| Auth required | ❌ Public | ✅ Yes |
| Endpoint | `/api/recommendations/related/{type}/{tmdb_id}` | `/api/recommendations/next/{type}` |
| Use-case UI | "Vì bạn đã xem" trên detail | "Tiếp nối đam mê" trên home |
| Library | `mlxtend>=0.23.0` | `torch>=2.2.0`, `numpy` |
| Artifact path | `data/recommender/fpgrowth/{movies,series}/` | `data/recommender/gru4rec/{movies,series}/` |
| Artifact `kind` | `"fpgrowth_v1"` | `"gru4rec_v1"` |

---

## Phần 5 — Pipeline triển khai 1-shot

```bash
cd fastapi-backend

# 1. Cài dependencies (mlxtend + torch CPU wheel ~150MB)
.venv\Scripts\pip install -r requirements.txt

# 2. Seed catalog (~300 phim từ TMDB)
.venv\Scripts\python scripts/seed_tmdb.py

# 3. Seed 40 demo users + watch_history (random.seed=42, idempotent)
.venv\Scripts\python scripts/seed_demo_users.py

# 4. Train cả 2 thuật toán × 2 content_type
.venv\Scripts\python scripts/train_fpgrowth.py    # ra rules.json
.venv\Scripts\python scripts/train_gru4rec.py     # ra model.pt + vocab

# 5. Run server
.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000
```

Sau khi seed nhiều content hoặc admin toggle visibility hàng loạt → re-run 2 train script. Stale artifact không crash inference (chỉ trả `[]` cho item ngoài vocab) nên việc retrain là defer-able.

---

## Phần 6 — Lưu ý privacy & operational

- **Privacy posture đã thay đổi**: cả 2 thuật toán đều train trên `watch_history` (không phải TMDB metadata thuần như recommender TF-IDF cũ). Artifact không chứa user_id, nhưng quá trình rebuild bắt buộc cần dữ liệu user. Xem `CLAUDE.md` cho ràng buộc đầy đủ.
- **Seed deterministic**: `random.seed(42)`, `torch.manual_seed(42)` → re-run cho ra kết quả y hệt (modulo timestamp `last_watched_at`).
- **Cache invalidation**:
  - FP-Growth: in-memory dict, drop qua `recommendation_service.reload(content_type)` hoặc restart process.
  - GRU4Rec: TTLCache 10 phút auto-expire; explicit drop qua `history_recommendation_service.reload(...)`. Predict cache cũng được clear khi reload.
- **Per-worker state**: cả 2 dùng module-level cache (`_STATE` dict), nên mỗi uvicorn worker load model 1 lần độc lập. Với 4 workers × `model.pt` 1-2 MB là chấp nhận được.
