## Project: Python Event-Driven Pub/Sub (RabbitMQ, MediatR-like)

### 🎯 Mục tiêu
- Xây dựng hệ thống Event-Driven Pub/Sub bằng **Python + RabbitMQ**
- Kiến trúc **Building Blocks**, domain-agnostic, testable, reusable
- Hành vi tương tự **MediatR (.NET)**

### 🚫 Không được phép
- Không gộp infrastructure và business logic
- Không hardcode domain trong building_blocks
- Không viết async sai ngữ cảnh
- Không phá kiến trúc đã định nghĩa

### 🧱 Kiến trúc bắt buộc
```
building_blocks/
  amqp_connection.py
  event_base.py
  handler_registry.py
  publisher.py
  subscriber.py

application/
  events.py
  handlers.py

main.py
```

### 📐 Coding Rules

#### Event
- `@dataclass`
- Có: domain, action, data, event_id, timestamp, version
- Routing key = `{domain}.{action}`
- JSON-safe serialization

#### Handler
- `async def handle(event)`
- 1 responsibility
- Không biết AMQP

#### Registry
- Wildcard pattern (`fnmatch`)
- Invoke tất cả handler phù hợp
- Không crash nếu 1 handler lỗi

#### AMQP
- `pika.BlockingConnection` **KHÔNG thread-safe**
- Không share connection giữa publisher & consumer
- Luôn `ack` hoặc `nack`

#### Async
- `asyncio.run()` chỉ khi chưa có event loop
- Không gọi trong async context

### 🧪 Test
- Test registry, matcher, invoke_all
- Không cần RabbitMQ
- Dùng pytest + pytest-asyncio

### 🧠 Bug Checklist
- Exchange/Queue đã declare?
- Ack/Nack mọi path?
- Infinite requeue?
- Pattern overlap?
- JSON serialization an toàn?

---