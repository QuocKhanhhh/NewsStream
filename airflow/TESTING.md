# Unit tests

Các test trong `tests/` chỉ kiểm tra logic của `src/`; HTTP, Redis và Kafka đều được mock nên không cần chạy service nào.

## Chạy local

Từ thư mục `airflow/`:

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

Muốn xem coverage:

```powershell
python -m pytest --cov=src --cov-report=term-missing
```

## Phạm vi hiện tại

- `clients`: HTTP, Redis, Kafka và context manager/serialization.
- `models`, `validators`: tạo ID, serialize datetime và kiểm tra bản tin.
- `sources`, `parser`: fetch RSS, parse RSS/Atom, làm sạch text.
- `proxy`: scrape bảng proxy, validate health và quản lý pool Redis.
- `exporters`: publish từng bản tin và đếm số bản tin thành công.
- `config`: giá trị mặc định và override bằng environment variable.

## Integration test RSS → Kafka → MongoDB

Từ thư mục gốc dự án, khởi động runtime:

```powershell
docker compose up -d --build
```

Sau khi Kafka, MongoDB và Kafka Connect ở trạng thái healthy:

```powershell
$env:RUN_INTEGRATION = "1"
python -m pytest tests/integration -m integration -q
```

Test dùng RSS fixture local, publish vào topic `rss_news`, rồi đợi MongoDB Sink Connector ghi document vào `newsdb.news`. Nếu Docker chưa chạy, test được skip có chủ đích.
