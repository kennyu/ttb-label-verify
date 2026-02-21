# Technical Preferences

## Python Development

### Package Management & Dependencies

- Use `uv` instead of `pip` for faster dependency resolution and more reliable package management.
- Use `pyproject.toml` for dependency management.
- Absolutely never use `poetry`.
- Always use virtual environments (`python -m venv` or `uv venv`) for project isolation - prevents dependency conflicts and ensures reproducible builds.
- Virtual environments are critical for Docker containers - create the venv in the container build process to ensure exact dependency matching between development and production environments.

### Project Structure & Imports

- The `src/` layout is outdated. Modern Python projects prefer flat structure with direct package directories.
- `__init__.py` files are not needed in Python 3.3+ with namespace packages. They add no value and just create maintenance overhead.
- Absolute imports over relative imports - they're clearer, easier to refactor, and work consistently across all contexts (tests, scripts, modules).
- Example: `from myproject.services.user import get_user` instead of `from ..services.user import get_user` or organizing everything under a meaningless `src/` directory.

### Library Preferences & Rationale

- Pydantic over dataclasses/dictionaries for automatic validation and typing.
- aioboto3/aiobotocore over boto3 for async AWS operations that don't block the event loop.
- aiohttp over httpx for HTTP client operations - more mature async ecosystem and better AWS SDK integration.
- FastAPI over Django/Flask for automatic API documentation, type validation, and async-first design.
- AsyncClient patterns over sync clients throughout the stack for non-blocking I/O.

### Async Programming Patterns

For a deep-dive into async patterns, see the Complete Async Programming Guide.

- Async/await consistently - never mix sync and async code paths.
- Async context managers for all resource management (database, HTTP clients, file operations).
- `asyncio.wait_for` handles a single awaitable object like await, but also lets you set a timeout to handle long-running tasks.
- Use `asyncio.gather()` for concurrent execution of tasks when wanting to await a collection of coroutines in the form of positional arguments. `gather` will return a list of results in the same order they were passed in and can also return tasks that encountered exceptions.
- `asyncio.as_completed` is an iterable that takes in any awaitable object and lets you handle tasks as they finish instead of all at once. It also has a timeout argument.
- ONLY use `asyncio.TaskGroup` when you want to cancel all other tasks if any task fails:

```python
import asyncio

async def do_something():
    return 1

async def do_something_else():
    return 2

async def main():
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(do_something())
        task2 = tg.create_task(do_something_else())

    print(f'Everything done: {task1.result()}, {task2.result()}')

asyncio.run(main())
```

- Use `asyncio.Semaphore(N)` + `asyncio.sleep()` together to control concurrent connections AND pace request velocity — prevents 429 errors and behavioral bot detection by making traffic patterns look human (start with `Semaphore(10)` + `sleep(0.5)` for ~20 req/sec).
- Async generators for streaming large datasets without memory bloat.
- Event loop management - let the framework handle loop lifecycle.
- Non-blocking I/O as the default for all external service calls.
- If stuck with blocking libraries (sync boto3, old database drivers) then use `ThreadPoolExecutor`. Likewise if we are looking for quick parallelism without completely rewriting to async.

### Type Safety & Code Quality

- Comprehensive type hints using modern union syntax (`str | None` over `Optional[str]`).
- Generic types for reusable code patterns (`list[T]`, `dict[str, Any]`).
- Protocol classes for defining interfaces without inheritance overhead.
- Return type annotations on all functions for IDE autocomplete and error catching.
- Strict mypy configuration to catch type errors early.

### Code Organization Philosophy

- **Functional over class-based** - Python classes are rarely necessary and add complexity without benefit.
- Use functions as the default. Classes should only exist when you need:
  - Shared mutable state across many operations (rare)
  - Complex inheritance hierarchies (almost never)
  - Framework requirements (Django models, FastAPI dependencies, etc.)
- Most "classes" are just namespaces pretending to be useful - a dict and some functions work better.
- Stateless functions compose better, test easier, and are simpler to reason about.
- If you think you need a class, you probably just need a function that returns a dict or Pydantic model.
- Data transformation pipelines should be chains of pure functions, not methods on objects.
- **Stateful objects create coupling** - avoid unless absolutely necessary for the problem domain.

### When to Use Pydantic BaseModel Instead of Classes

- **API request/response validation** - Pydantic models provide automatic validation, serialization, and documentation.
- **Configuration objects** - Type-safe config with validation beats hand-rolled classes.
- **Data transfer objects** - When passing structured data between layers (API → service → DB).
- **JSON schema generation** - Automatic OpenAPI/JSON schema for free.
- **Type coercion needs** - Pydantic handles string → int, datetime parsing, etc. automatically.

Example of Pydantic > Classes for API endpoints:

```python
from pydantic import BaseModel, Field

# Good: Pydantic for request validation
class SubscriptionRequest(BaseModel):
    tier: SubscriptionTier

class CreditPurchaseRequest(BaseModel):
    amount: int = Field(..., gt=0, description="Number of credits to purchase")

@router.post("/credits/purchase", response_model=CreditBalance)
async def purchase_credits(
    credit_data: CreditPurchaseRequest,  # Automatic validation!
    user_data: UserData = Depends(get_user_with_profile)
):
    # FastAPI automatically validates, coerces types, and generates OpenAPI docs
    # No need for manual validation or custom classes
    credits = await subscription_service.purchase_credits(
        user_id, credit_data.amount, transaction_id
    )
    return credits
```

**Why this is better than a class:**

- Automatic validation (amount > 0 checked before your code runs)
- Type coercion (string "5" → int 5)
- JSON serialization built-in
- OpenAPI schema generation
- IDE autocomplete everywhere
- No need to write `__init__`, validation methods, or serialization logic

**When NOT to use Pydantic:**

- High-performance serialization: If you are processing >10k req/sec, Pydantic's overhead (10-50µs) adds up. Use `msgspec` instead — it's 10-50x faster and strictly typed (Rust-like).
- Internal utility functions: Just use `TypedDict` or simple classes. Pydantic is for *boundaries* (API, DB, Config).

### Pydantic Best Practices & Pitfalls

- Pydantic V2 coerces types by default (e.g., `age="23"` becomes `23`). For robust APIs, enable strict mode to catch client errors early:

```python
model_config = ConfigDict(strict=True)
```

- Don't create a dummy `UsersList` model just to validate a list of users. Use `TypeAdapter`:

```python
ta = TypeAdapter(list[User])
users = ta.validate_json(json_data)
```

- Don't manually add `alias="firstName"` to every field. Use `alias_generator` to handle `snake_case` (Python) ↔ `camelCase` (JSON) conversion automatically.
- Always remember `model.model_dump(by_alias=True)` when sending data back to the client, otherwise you'll leak your internal snake_case names.

### Error Handling & Resilience

- Structured exception hierarchy - custom exceptions for different error categories.
- Retry logic with exponential backoff for transient failures.
- Graceful degradation when optional services are unavailable.
- Comprehensive logging with structured data for debugging and monitoring.

### Testing & Development

- Unit tests are a waste of time. However if you must...
- **Pytest over unittest:** Use pytest for all testing - cleaner syntax, better assertion introspection, superior plugin ecosystem.
- **Pytest fixtures:** Leverage fixtures for test setup/teardown and dependency injection - they're more powerful and composable than unittest's setUp/tearDown.
- **Pytest mocking over unittest.mock:** Use `pytest-mock` (wraps unittest.mock with better pytest integration) or `pytest.MonkeyPatch` for cleaner, more maintainable mocks.
- **Fixture scope management:** Use appropriate fixture scopes (`function`, `class`, `module`, `session`) to optimize test performance without sacrificing isolation.
- Mock external dependencies rather than hitting real services in tests, obviously.

---

## Database & Data Management

### Schema Design & Management

- SQL migrations over ORM migrations for transparent, reviewable schema changes.
- Database views over complex joins in application code for performance.
- Normalized schemas with strategic denormalization (arrays).
- Row Level Security over application-level access control for data security.

---

## API & Web Development

### API Design

- RESTful resource design with consistent URL patterns and HTTP methods.
- JSON API responses with standardized error formats across all endpoints.
- Middleware for cross-cutting concerns (authentication, logging, error handling).
- Route organization by domain rather than by HTTP method or function.
- Input validation at API boundary using request/response models.
- Consistent error handling with proper HTTP status codes and error details.

---

## Frontend Development

### Technology Choices & Patterns

- TypeScript over JavaScript for compile-time error detection.
- Component composition over inheritance for UI building.
- Custom hooks for stateful logic reuse across components.
- Server state management separate from client state.
- Progressive enhancement - core functionality works without JavaScript.
- Bundle optimization - code splitting and lazy loading by default.
- Native `fetch` over axios in frontend to reduce bundle size and leverage browser optimizations.

---

## Security & Configuration

### Security Practices

- Environment-based configuration with validation at startup.
- Secrets management through environment variables, never hardcoded.
- Principle of least privilege in service account permissions.
- Input sanitization at all system boundaries.
- Authentication middleware rather than per-endpoint auth checks.
- HTTPS/TLS everywhere for data in transit.

---

## Performance & Scalability

### Performance Optimization

- Lazy loading of expensive resources until actually needed.
- Connection reuse through singleton patterns and context managers.
- Async I/O to maximize throughput on single-threaded event loops.
- Caching strategies at appropriate layers (database, application, CDN).
- Resource pooling for expensive-to-create objects.

---

## Infrastructure & Deployment

### Infrastructure Management

- Infrastructure as Code for reproducible environments.
- Containerization for consistent runtime environments.
- Serverless-first for auto-scaling and cost optimization.
- Multi-environment parity - development mirrors production.
- Blue-green deployments for zero-downtime releases.
- Configuration management separated from application code.

---

## Observability & Monitoring

### Monitoring & Debugging

- Structured logging with consistent field names and log levels.
- Distributed tracing for request flows across multiple services.
- Error aggregation with context and stack traces.

---

## AI/ML Integration

### AI/ML Best Practices

- Model-agnostic interfaces for easy provider switching.
- Prompt versioning and testing as first-class development concerns.
- Token usage monitoring for cost control and optimization.
- Response validation with schema enforcement and fallback handling.
- A/B testing frameworks for comparing model performance.
- Offline evaluation before deploying new models or prompts.
