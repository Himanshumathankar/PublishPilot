# TWPublisher

TWPublisher is a deterministic, multi-site WordPress publishing workspace. It imports editor-approved source articles, preserves their wording, formatting, order, images, captions, tables, and links, and publishes them through the WordPress REST API. It does not rewrite, summarize, improve, or generate content.

The DOCX workflow is implemented: sequential parsing, preview, WordPress category/media/post operations, featured images, Rank Math metadata, draft/publish, and history. Google Docs and Sheets intentionally follow the complete DOCX workflow.

## Architecture

- `frontend/`: Next.js 16, React 19, TypeScript, Tailwind CSS
- `backend/`: FastAPI, Pydantic, async SQLAlchemy, structured JSON logging
- `backend/migrations/`: Alembic migrations for PostgreSQL
- `docs/`: decisions and integration documentation
- PostgreSQL 16 stores job/article state, image metadata, WordPress IDs, and publish logs

Every source adapter must output the common ordered `ArticleDocument` defined in `backend/app/schemas/article.py`. This keeps parsing separate from validation, rendering, and publishing. See [architecture details](docs/architecture.md).

## Prerequisites

- Docker Desktop with Compose, recommended for local development
- Or Node.js 22+, npm 10+, Python 3.12–3.14, and PostgreSQL 16

## Docker setup

1. Copy `.env.example` to `.env`.
2. Replace `POSTGRES_PASSWORD`, `APP_SECRET_KEY`, `APP_USERNAME`, and `APP_PASSWORD`. Keep `DATABASE_URL` consistent with the database password.
3. Run `docker compose up --build` (or `make dev`).
4. Open the frontend at <http://localhost:3000> and sign in with `APP_USERNAME` and
   `APP_PASSWORD`. Add WordPress websites from **Settings**. API docs are at
   <http://localhost:8000/docs>.

The backend waits for PostgreSQL, applies `alembic upgrade head`, then starts. Named volumes retain database and development dependency data. Stop services with `docker compose down`; add `--volumes` only when intentionally deleting local data.

Health endpoints:

- `GET /api/v1/health/live`: process liveness
- `GET /api/v1/health/ready`: database readiness

## Local setup without Docker

Create the PostgreSQL user/database represented by `DATABASE_URL`, then:

```bash
cp .env.example .env
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

For host-based backend execution, change the database host in `DATABASE_URL` from `db` to `localhost`.

## Environment variables

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL connection URL |
| `APP_ENV` | `development`, `test`, or `production` |
| `APP_SECRET_KEY` | At least 32 random characters in deployed environments |
| `APP_USERNAME` | Username used to sign in to TWPublisher |
| `APP_PASSWORD` | Strong password used to sign in to TWPublisher |
| `BACKEND_CORS_ORIGINS` | Comma-separated allowed browser origins |
| `MAX_UPLOAD_SIZE_MB` | DOCX upload ceiling; defaults to 25 |
| `MAX_DOCX_UNCOMPRESSED_MB` | Expanded DOCX archive safety ceiling; defaults to 200 |
| `WORDPRESS_MEDIA_MAX_MB` | Per-image WordPress upload ceiling; defaults to 1 for Colitco |
| `NEXT_PUBLIC_API_URL` | Browser-visible API base URL |
| `WORDPRESS_BASE_URL` | WordPress origin, without `/wp-json` |
| `WORDPRESS_USERNAME` | Dedicated automation user |
| `WORDPRESS_APPLICATION_PASSWORD` | Application Password, never the normal password |
| `RANK_MATH_ENDPOINT` | Optional site-specific Rank Math REST endpoint |
| `GOOGLE_APPLICATION_CREDENTIALS` | Google service credential path for later phases |

Never commit `.env`, Application Passwords, database passwords, or Google credentials.

## Database and migrations

The first migration creates `article_jobs`, `articles`, `article_images`, and `publish_logs`, plus constrained source/status enums. Apply changes with `alembic upgrade head` or `make migrate`. Create future migrations from `backend/` with `alembic revision --autogenerate -m "description"`, then review generated SQL before applying it.

## Testing and quality checks

With local dependencies installed:

```bash
cd backend && pytest && ruff check app tests
cd frontend && npm test && npm run lint && npm run build
```

Or use `make test` and `make lint` with Docker. Phase 1 tests exercise API liveness/readiness, the common ordered article model, the no-body-H1 invariant, and the upload UI state.

## DOCX article format

The intended source begins with exact `Meta Title:`, `Meta Description:`, and `URL Slug:` fields, followed by one H1 post title and ordered body content. The DOCX parser will walk WordprocessingML body elements sequentially—not `document.paragraphs` and `document.tables` independently—so paragraphs, images, captions, headings, lists, and tables retain their original order. The first H1 is removed from body blocks and used as the WordPress title. H2/H3 remain body headings.

No content field is rewritten. Metadata lines are mapped and excluded from the body. Hyperlinks and displayed captions remain exact. Image filenames alone are sanitized and deduplicated.

## Publishing workflow

The target DOCX milestone is: upload → safe parse → validate → preview → manually choose category and featured image → upload all media → render WordPress HTML → create draft/publish → apply Rank Math data → verify → record history. Draft is the default test path. A media failure prevents post creation.

### Using the editor

1. Open <http://localhost:3000> and sign in with the TWPublisher credentials configured as
   `APP_USERNAME` and `APP_PASSWORD`.
2. Open **Settings** to add each WordPress website with its dedicated username and Application
   Password, then configure its Rank Math endpoint. Passwords are encrypted before database
   storage; a normal WordPress account password must not be used.
3. From the dashboard, open **New article** and select a `.docx` file.
4. Click **Process article**. The application extracts the source and opens its preview without publishing anything.
5. Confirm the title, metadata, block order, formatting, tables, images, filenames, and captions.
6. Select a category and author fetched live from WordPress, then upload the featured image.
7. Use **Save as draft** for the initial workflow. Use **Publish** only after verifying the preview.
8. Review all processed and failed imports under **History**. Filter by status/source, search
   by title or source, and open a record to inspect WordPress IDs, image upload outcomes, and
   every publish attempt.

If WordPress is not configured, local DOCX processing and preview still work. The preview displays a clear `WORDPRESS_NOT_CONFIGURED` message where categories would otherwise load.

## WordPress setup

1. Create a least-privilege WordPress user dedicated to publishing.
2. Under that user's profile, create an Application Password named for this service.
3. Set `WORDPRESS_BASE_URL`, `WORDPRESS_USERNAME`, and `WORDPRESS_APPLICATION_PASSWORD`.
4. Ensure HTTPS and that `/wp-json/wp/v2/categories`, `/media`, and `/posts` are reachable.
5. Do not use or store the administrator's normal password.

The application tests connectivity, fetches categories, uploads media, creates draft/published posts, assigns `featured_media`, and stores the returned post URL.

## Rank Math setup

WordPress core REST may not expose Rank Math's `rank_math_title` and `rank_math_description` post meta. The integration first tries registered REST meta and verifies the returned values. If that reports `RANK_MATH_UPDATE_ERROR`, install `wordpress-plugin/twpublisher-connector.zip` from **Plugins → Add Plugin → Upload Plugin**, activate **TWPublisher Connector**, and set the site's Rank Math endpoint to `/wp-json/twpublisher/v1/rank-math`. The endpoint requires `edit_post` permission and updates only the two approved fields. Never edit WordPress core.

When migrating from **Article Publisher Rank Math Bridge** or **PublishPilot Connector**, deactivate and delete the old plugin before uploading TWPublisher Connector so WordPress does not load multiple copies. Existing saved legacy endpoint URLs remain valid. Standard automatic updates become available after the plugin is approved and hosted in the WordPress.org Plugin Directory; the plugin does not bypass the directory with a custom updater.

## Google Docs API setup

Google Docs and Google Sheets URL ingestion are implemented. Create a Google Cloud project, enable the Google Docs, Drive, and Sheets APIs, create a service account, download its JSON key as `secrets/google-service-account.json`, and share each source file with the service-account email as a Viewer. Set `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/google-service-account.json`; Compose mounts the ignored `secrets/` directory read-only. Application Default Credentials are used when the variable is empty and ADC is available. Credentials remain outside the repository.

The first Sheets tab uses a flexible `Field | Value` layout; field order and row numbers do not matter. Recognized metadata fields are `Meta Title`, `Meta Description`, `URL Slug`, and `Article Title`. Use `Article URL` to delegate the body to a Google Doc while allowing sheet metadata to override matching fields. For direct sheet content, use repeated `Paragraph`, `Heading 2`, `Heading 3`, `Bullet Item`, and `Numbered Item` rows, or one `Article Content` value separated by blank lines.

## Common errors and troubleshooting

- `DATABASE_UNAVAILABLE`: verify PostgreSQL health and that `DATABASE_URL` uses `db` in Compose or `localhost` on the host.
- Backend does not start: run `docker compose logs backend db`; migration failures usually indicate mismatched credentials or a stale development volume.
- Browser cannot reach API: verify `NEXT_PUBLIC_API_URL` and `BACKEND_CORS_ORIGINS`, then rebuild the frontend because public variables are bundled.
- Port conflict: change the host side of a Compose port mapping, not the service's internal port.
- WordPress 401/403 in later phases: confirm the dedicated username, Application Password, HTTPS/proxy authorization headers, and role capabilities.
- Rank Math values absent in later phases: confirm its meta is REST-exposed or install the documented endpoint; publishing must report `RANK_MATH_UPDATE_ERROR`, not silently succeed.

## Production recommendations

Build the production Docker stages, run migrations as a one-off release task, put services behind TLS, use a managed PostgreSQL database with backups, store secrets in the platform secret manager, restrict CORS, disable API docs, add organization SSO at the application or trusted access-proxy layer, use persistent centralized logs, scan dependencies/images, apply CPU/memory and request-size limits, and monitor readiness plus publish failures. Use object storage only if temporary files must span workers; source DOCX retention is unnecessary by default.

## Delivery order

1. Foundation (complete)
2. WordPress REST integration
3. Rank Math integration
4. Sequential DOCX parser and fixtures
5. Inline image pipeline
6. Featured image
7. Preview
8. Complete DOCX publish workflow (implemented)
9. Google Docs
10. Google Sheets
11. History/logging UI and APIs (complete)
12. Hardening and full acceptance suite (complete)
