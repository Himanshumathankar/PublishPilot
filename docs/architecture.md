# Architecture

All import adapters produce one ordered `ArticleDocument`. Downstream validation, rendering, media upload, Rank Math mapping, and publishing consume that representation and never branch on the original source type.

```text
DOCX parser ───────┐
Google Docs parser ├─> ArticleDocument ─> validation ─> preview/renderer ─> publishing service
Sheets parser ─────┘                                           │
                                                              ├─> WordPress media/posts
                                                              └─> Rank Math adapter
```

The API owns parsing and publishing. PostgreSQL stores workflow state and WordPress identifiers, not credentials or source DOCX files. The browser receives safe preview data and initiates explicit draft/publish actions. Uploaded files use temporary storage and are deleted after processing.

## Common representation

`ArticleDocument` contains source-exact metadata and an ordered, discriminated block list. Body headings allow only levels 2 and 3 because the first source H1 becomes the post title. Blocks cover paragraphs (safe inline HTML), headings, lists, images, and tables. Image blocks refer to extracted assets using stable internal IDs until WordPress URLs are available.

## Publishing consistency

The planned publishing service validates first, uploads all media before post creation, builds final HTML only after uploads succeed, creates the post, applies and verifies Rank Math metadata, and finally commits local success state. Every attempt writes a `publish_logs` record. A failed pre-post media operation cannot produce a partial post.

## Security boundaries

- DOCX and images are untrusted input; enforce size, MIME, archive, XML, and image limits before parsing.
- WordPress Application Password and Google credentials are environment-only secrets.
- Preview HTML must pass a strict server-side allowlist sanitizer before reaching the browser.
- API errors expose stable codes and safe messages; technical context remains in structured server logs.
- Production authentication must sit in front of all article routes; the Phase 1 login view is only the UI boundary.

