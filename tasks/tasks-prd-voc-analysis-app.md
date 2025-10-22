# Task List: Voice of Customer Analysis Application

## Relevant Files

### Backend Core
- `voc_app/main.py` - FastAPI application entry point
- `voc_app/config.py` - Configuration management (env vars, settings)
- `voc_app/database.py` - SQLite database connection and session management
- `voc_app/models/` - SQLAlchemy ORM models directory
- `voc_app/models/feedback.py` - Feedback data model
- `voc_app/models/source.py` - Data source configuration model
- `voc_app/models/insight.py` - Extracted insight model
- `voc_app/models/alert.py` - Alert configuration and history model
- `voc_app/schemas/` - Pydantic schemas for API validation
- `voc_app/api/` - API route handlers directory
- `voc_app/api/insights.py` - Insights API endpoints
- `voc_app/api/sources.py` - Source management endpoints
- `voc_app/api/alerts.py` - Alert configuration endpoints
- `voc_app/api/exports.py` - Data export endpoints

### Crawling & Processing
- `voc_app/crawlers/` - Crawler implementations directory
- `voc_app/crawlers/base.py` - Base crawler class
- `voc_app/crawlers/reddit.py` - Reddit scraper using Crawl4AI
- `voc_app/crawlers/twitter.py` - Twitter/X scraper
- `voc_app/crawlers/youtube.py` - YouTube comments scraper
- `voc_app/crawlers/review_sites.py` - Review site scrapers (G2, Trustpilot, etc.)
- `voc_app/crawlers/social_media.py` - Facebook, LinkedIn scrapers
- `voc_app/crawlers/forums.py` - Forum scrapers (Quora, etc.)
- `voc_app/crawlers/search.py` - Google search result scraper
- `voc_app/processors/` - Data processing pipeline
- `voc_app/processors/cleaner.py` - Content cleaning and deduplication
- `voc_app/processors/extractor.py` - GPT-5 powered insight extraction
- `voc_app/processors/classifier.py` - Theme and sentiment classification
- `voc_app/processors/analyzer.py` - Trend and pattern analysis

### Background Tasks
- `voc_app/tasks/` - Celery task definitions
- `voc_app/tasks/crawl_tasks.py` - Scheduled crawling tasks
- `voc_app/tasks/processing_tasks.py` - Data processing tasks
- `voc_app/tasks/alert_tasks.py` - Alert monitoring and notification tasks
- `voc_app/celery_app.py` - Celery application configuration
- `voc_app/utils/redis_client.py` - Redis client for caching and queue

### Analytics & Reporting
- `voc_app/analytics/` - Analytics engine
- `voc_app/analytics/sentiment.py` - Sentiment analysis logic
- `voc_app/analytics/themes.py` - Theme clustering and trend detection
- `voc_app/analytics/reports.py` - AI-generated report creation
- `voc_app/services/` - Business logic services
- `voc_app/services/alert_service.py` - Alert detection and notification
- `voc_app/services/export_service.py` - Data export functionality
- `voc_app/services/webhook_service.py` - Webhook integrations

### Frontend Application
- `voc_app/frontend/` - React application root
- `voc_app/frontend/package.json` - Node dependencies
- `voc_app/frontend/src/` - React source code
- `voc_app/frontend/src/main.tsx` - Application entry point
- `voc_app/frontend/src/App.tsx` - Root component with routing
- `voc_app/frontend/src/pages/Dashboard.tsx` - Main dashboard page
- `voc_app/frontend/src/pages/Insights.tsx` - Insights list and detail page
- `voc_app/frontend/src/pages/Sources.tsx` - Source configuration page
- `voc_app/frontend/src/pages/Alerts.tsx` - Alert management page
- `voc_app/frontend/src/pages/Reports.tsx` - Reports and analytics page
- `voc_app/frontend/src/components/` - Reusable components
- `voc_app/frontend/src/components/charts/` - Chart components
- `voc_app/frontend/src/components/ui/` - shadcn/ui components
- `voc_app/frontend/src/lib/api.ts` - API client
- `voc_app/frontend/src/lib/utils.ts` - Utility functions
- `voc_app/frontend/src/hooks/` - Custom React hooks
- `voc_app/frontend/tailwind.config.js` - TailwindCSS configuration
- `voc_app/frontend/vite.config.ts` - Vite build configuration

### Testing
- `voc_app/tests/` - Test suite directory
- `voc_app/tests/test_crawlers.py` - Crawler tests
- `voc_app/tests/test_processors.py` - Processor tests
- `voc_app/tests/test_api.py` - API endpoint tests
- `voc_app/tests/test_analytics.py` - Analytics tests
- `voc_app/tests/conftest.py` - Pytest fixtures

### Configuration & Deployment
- `voc_app/.env.example` - Environment variables template
- `voc_app/requirements.txt` - Python dependencies
- `voc_app/alembic/` - Database migration directory
- `voc_app/alembic/env.py` - Alembic configuration
- `voc_app/Dockerfile` - Docker container definition
- `voc_app/docker-compose.yml` - Multi-container orchestration
- `voc_app/README.md` - Project documentation
- `voc_app/.gitignore` - Git ignore rules

### Notes

- Unit tests should accompany every new module in `voc_app/tests/`.
- Use `uv run pytest` to execute the Python test suite.
- Frontend tests should run with `npm test` inside `voc_app/frontend/` once the React app is scaffolded.

## Tasks

### Phase 1: Foundation & Core Pipeline (Weeks 1-3)

-- [x] 1.0 Project Setup & Infrastructure
  - [x] 1.1 Scaffold `voc_app/` Python package and FastAPI application entrypoint `voc_app/main.py`.
  - [x] 1.2 Configure settings management in `voc_app/config.py` with environment variable loading and defaults per environment.
  - [x] 1.3 Define dependency management files (`voc_app/requirements.txt`, `voc_app/frontend/package.json`) and lock versions aligning with workspace standards.
  - [x] 1.4 Establish development tooling (pre-commit hooks, lint commands, formatter) without altering existing repo conventions.

- [x] 2.0 Database Schema & Models
  - [x] 2.1 Draft ERD covering feedback, insights, sources, alerts, and relationships.
  - [x] 2.2 Implement SQLAlchemy models in `voc_app/models/` with metadata, indexes, and relationships.
  - [x] 2.3 Configure Alembic migrations and generate initial migration for schema.
  - [x] 2.4 Create `voc_app/database.py` session handling with dependency injection for FastAPI.

- [x] 3.0 Basic Crawl4AI Integration (Reddit & Twitter)
  - [x] 3.1 Implement shared `BaseCrawler` abstraction in `voc_app/crawlers/base.py` using Crawl4AI adaptive crawling.
  - [x] 3.2 Build Reddit crawler leveraging subreddit/topic configuration and citation preservation.
  - [x] 3.3 Build Twitter/X crawler utilizing keyword and hashtag queries with rate-limit awareness.
  - [x] 3.4 Store raw crawl outputs with metadata in database and file storage if required.

- [x] 4.0 Data Processing Pipeline Foundation
  - [x] 4.1 Implement cleaning utility in `voc_app/processors/cleaner.py` (noise removal, deduplication candidates).
  - [x] 4.2 Create ingestion pipeline orchestrator to move crawled records through cleaning to staging tables.
  - [x] 4.3 Define validation checks for mandatory fields, timestamps, and source attribution.
  - [x] 4.4 Add unit tests covering pipeline happy/malformed paths.

- [x] 5.0 CLI Interface for Testing
  - [x] 5.1 Create `voc_app/cli.py` to trigger crawls, processing, and status summaries.
  - [x] 5.2 Provide CLI flags for selecting sources, date ranges, and dry-run modes.
  - [x] 5.3 Document usage in `voc_app/README.md` and ensure CLI respects environment configs.
  - [x] 5.4 Add CLI-specific tests validating command execution using pytest Click/typer helpers.

### Phase 2: Intelligence & Analysis (Weeks 4-5)

- [x] 6.0 GPT-5 Insight Extraction System
  - [x] 6.1 Define prompt templates and schemas for GPT-5 extraction covering sentiment, themes, pain points, and metadata.
  - [x] 6.2 Implement `voc_app/processors/extractor.py` with batching, retry logic, and cost tracking.
  - [x] 6.3 Persist structured insight results to normalized tables and maintain source citations.
  - [x] 6.4 Write unit tests with mocked GPT-5 responses ensuring parsing robustness.

- [x] 7.0 Expand Data Sources (Add 4 More)
  - [x] 7.1 Prioritize and implement crawlers for YouTube, Trustpilot, Quora, and G2 leveraging shared base class.
  - [x] 7.2 Add configuration schemas for each new source in `voc_app/models/source.py` and admin UI placeholders.
  - [x] 7.3 Update scheduling logic to accommodate per-source cadence and throttling.
  - [x] 7.4 Expand tests to cover new crawler adapters and integration flows.

- [x] 8.0 Theme Classification & Clustering
  - [x] 8.1 Implement rule-based + LLM-assisted theme mapper in `voc_app/processors/classifier.py`.
  - [x] 8.2 Add clustering routine for emerging themes using embeddings + Redis cache.
  - [x] 8.3 Store theme assignments and trend metadata for analytics queries.
  - [x] 8.4 Validate classification accuracy with sample datasets and adjust prompts/thresholds.

- [x] 9.0 Background Task System (Celery)
  - [x] 9.1 Configure Celery app with Redis broker/back-end in `voc_app/celery_app.py`.
  - [x] 9.2 Implement crawl scheduling tasks with retry and rate-limit safeguards.
  - [x] 9.3 Implement processing tasks for extraction, classification, and alert detection pipelines.
  - [x] 9.4 Add monitoring endpoints/logging for task success/failures and write tests using Celery test harness.

- [x] 10.0 Alert Detection Engine
  - [x] 10.1 Design alert rules model supporting sentiment thresholds, volume spikes, keyword triggers, and competitor mentions.
  - [x] 10.2 Implement `voc_app/services/alert_service.py` evaluating rules against processed insights.
  - [x] 10.3 Create notification channel integrations (email, webhook) with templates.
  - [x] 10.4 Write tests simulating alert conditions and verifying notifications fire correctly.

### Phase 3: API & Integration Layer (Week 6)

- [x] 11.0 FastAPI REST Endpoints
  - [x] 11.1 Implement CRUD endpoints for sources, crawls, insights, alerts in `voc_app/api/` modules.
  - [x] 11.2 Apply dependency-based auth placeholder (API key header) and rate limiting middleware.
  - [x] 11.3 Ensure pagination, sorting, and error handling align with API guidelines.
  - [x] 11.4 Add integration tests hitting FastAPI app with in-memory database fixtures.

- [ ] 12.0 Filtering & Search Functionality
  - [ ] 12.1 Implement query filters for date ranges, sentiment, themes, platforms, and keywords.
  - [ ] 12.2 Add full-text search leveraging SQLite FTS or fallback search strategy.
  - [ ] 12.3 Optimize query performance with indexes and caching for common requests.
  - [ ] 12.4 Extend API tests to cover filter combinations and edge cases.

- [ ] 13.0 Export System (CSV, JSON, Excel)
  - [ ] 13.1 Implement export serializers in `voc_app/services/export_service.py` for supported formats.
  - [ ] 13.2 Add asynchronous export jobs with status tracking and download endpoints.
  - [ ] 13.3 Ensure data anonymization rules apply before export delivery.
  - [ ] 13.4 Write tests verifying export correctness and permissions.

- [ ] 14.0 Webhook Integration System
  - [ ] 14.1 Design webhook subscription model allowing external systems to register endpoints.
  - [ ] 14.2 Implement webhook dispatch for alerts and scheduled summaries with retry/backoff.
  - [ ] 14.3 Add signature/authentication support for outgoing webhooks.
  - [ ] 14.4 Provide tests mocking webhook receivers and failure scenarios.

- [ ] 15.0 API Documentation & Testing
  - [ ] 15.1 Generate OpenAPI spec automatically and curate docs in `voc_app/docs/` (or README section).
  - [ ] 15.2 Add ReDoc/Swagger UI routes for developer access.
  - [ ] 15.3 Create API usage examples and Postman collection.
  - [ ] 15.4 Finalize contract tests ensuring docs match implemented behavior.

### Phase 4: Dashboard & Visualization (Weeks 7-9)

- [ ] 16.0 React Frontend Foundation
  - [ ] 16.1 Initialize Vite + React + TypeScript project inside `voc_app/frontend/` with TailwindCSS and shadcn/ui setup.
  - [ ] 16.2 Implement global layout, navigation shell, and responsive design system.
  - [ ] 16.3 Configure API client wrapper with auth headers and error handling.
  - [ ] 16.4 Add frontend unit tests and linting pipeline (Vitest/Testing Library).

- [ ] 17.0 Authentication & Access Control
  - [ ] 17.1 Implement API key management UI and secure storage (local env for MVP).
  - [ ] 17.2 Add login/key entry flow gating dashboard routes.
  - [ ] 17.3 Integrate backend auth middleware with frontend token handling.
  - [ ] 17.4 Add access control tests covering protected route redirects.

- [ ] 18.0 Main Dashboard with Metrics
  - [ ] 18.1 Implement overview cards for sentiment index, volume trends, top pain points.
  - [ ] 18.2 Integrate time-series chart for sentiment trend pulling aggregated API data.
  - [ ] 18.3 Display source distribution and customer journey breakdown widgets.
  - [ ] 18.4 Add loading/error states and snapshot tests.

- [ ] 19.0 Insights List & Detail Views
  - [ ] 19.1 Build table/list view with sorting, pagination, and quick filters.
  - [ ] 19.2 Create detail drawer/modal with full context, citations, GPT summary.
  - [ ] 19.3 Enable tagging/bookmarking of insights for follow-up.
  - [ ] 19.4 Add tests for list interactions and API calls.

- [ ] 20.0 Interactive Charts & Visualizations
  - [ ] 20.1 Implement word cloud, bar charts, and comparison charts using Recharts or Chart.js wrappers.
  - [ ] 20.2 Add cross-filter interactions between charts and insight lists.
  - [ ] 20.3 Ensure accessibility (ARIA labels, color contrast) for all visualizations.
  - [ ] 20.4 Write visual regression or snapshot tests for key charts.

- [ ] 21.0 Source Management UI
  - [ ] 21.1 Create source configuration page with forms for adding/editing crawlers.
  - [ ] 21.2 Surface crawl status, last run, error messages.
  - [ ] 21.3 Allow enabling/disabling sources and adjusting schedules.
  - [ ] 21.4 Add tests covering form validation and API mutation flows.

- [ ] 22.0 Alert Configuration Interface
  - [ ] 22.1 Provide rule builder UI for thresholds, keywords, competitor monitoring.
  - [ ] 22.2 Display alert history with filtering and acknowledgment workflow.
  - [ ] 22.3 Integrate notification channel settings (email, webhook, Slack placeholder).
  - [ ] 22.4 Add tests covering rule creation/editing and UI states.

### Phase 5: Advanced Features & Polish (Weeks 10-11)

- [ ] 23.0 Remaining Data Sources (LinkedIn, Facebook, Forums, Google)
  - [ ] 23.1 Build crawler adapters for LinkedIn, Facebook, industry forums, and Google search discovery.
  - [ ] 23.2 Handle authentication or public scraping constraints with Crawl4AI stealth features.
  - [ ] 23.3 Add platform-specific normalization and metadata mapping.
  - [ ] 23.4 Update scheduling/config UI to support new sources and extend tests accordingly.

- [ ] 24.0 AI-Generated Reports
  - [ ] 24.1 Implement report templates (weekly summary, theme deep dive, executive highlights).
  - [ ] 24.2 Automate GPT-5 summarization pipeline with cost controls and caching.
  - [ ] 24.3 Add delivery options (PDF, HTML export, email) via export service.
  - [ ] 24.4 Write tests validating report structure and fallback behavior when LLM unavailable.

- [ ] 25.0 Competitive Comparison Views
  - [ ] 25.1 Extend data model to store competitor tags and comparisons.
  - [ ] 25.2 Implement backend analytics calculating sentiment deltas and market share signals.
  - [ ] 25.3 Build frontend comparison matrix and trend charts.
  - [ ] 25.4 Test comparison logic with seeded data ensuring accuracy.

- [ ] 26.0 Advanced Filtering & Search UI
  - [ ] 26.1 Add multi-select filters, saved views, and query builder in frontend.
  - [ ] 26.2 Persist filter preferences per user/session via API.
  - [ ] 26.3 Optimize API endpoints for complex query combinations.
  - [ ] 26.4 Add integration tests verifying end-to-end filtering UX.

- [ ] 27.0 Real-time Updates (WebSocket)
  - [ ] 27.1 Implement WebSocket endpoint broadcasting new insights and alerts.
  - [ ] 27.2 Integrate frontend listeners updating dashboard widgets live.
  - [ ] 27.3 Add throttling/debouncing to prevent UI overload.
  - [ ] 27.4 Write tests for WebSocket handshake and message handling.

- [ ] 28.0 Admin Monitoring Dashboard
  - [ ] 28.1 Build backend metrics endpoints exposing crawl success rates, task queue stats, API usage.
  - [ ] 28.2 Create admin UI panel visualizing system health and logs.
  - [ ] 28.3 Implement alerting for infrastructure issues (task failures, quota usage).
  - [ ] 28.4 Add tests ensuring metrics accuracy and access control restrictions.

### Phase 6: Testing, Documentation & Deployment (Week 12)

- [ ] 29.0 Comprehensive Test Suite
  - [ ] 29.1 Achieve >80% coverage across backend modules with unit and integration tests.
  - [ ] 29.2 Implement frontend e2e tests (Playwright/Cypress) covering critical flows.
  - [ ] 29.3 Automate test execution in CI pipeline with environment setup scripts.
  - [ ] 29.4 Document test commands and add troubleshooting section.

- [ ] 30.0 Performance Optimization
  - [ ] 30.1 Benchmark crawl throughput, processing latency, and API response times.
  - [ ] 30.2 Optimize bottlenecks (query plans, Celery concurrency, caching) based on metrics.
  - [ ] 30.3 Implement rate monitoring to ensure compliance with external platform limits.
  - [ ] 30.4 Re-run benchmarks to confirm improvements and capture in reports.

- [ ] 31.0 Documentation & User Guides
  - [ ] 31.1 Produce setup guide covering local, staging, and prod environments in `voc_app/README.md`.
  - [ ] 31.2 Create user manual detailing dashboard usage, alerts, and reports.
  - [ ] 31.3 Document API reference with example requests/responses.
  - [ ] 31.4 Compile troubleshooting and FAQ section based on known challenges.

- [ ] 32.0 Docker Deployment Setup
  - [ ] 32.1 Author Dockerfile and docker-compose for API, worker, and frontend services respecting existing patterns.
  - [ ] 32.2 Configure environment variable management and secrets handling for containers.
  - [ ] 32.3 Add build/test steps to CI to validate container images.
  - [ ] 32.4 Document deployment instructions for cloud environments.

- [ ] 33.0 Production Readiness & Security
  - [ ] 33.1 Conduct security review (dependency audit, secret scanning, auth hardening).
  - [ ] 33.2 Implement logging, monitoring, and alerting hooks for production.
  - [ ] 33.3 Finalize GDPR/data retention compliance configuration and anonymization scripts.
  - [ ] 33.4 Prepare go-live checklist including rollback and support plan.

---

**Status:** Parent tasks generated. Awaiting confirmation to proceed with sub-tasks.

**Next Step:** Respond with "Go" to generate detailed sub-tasks for each parent task.
