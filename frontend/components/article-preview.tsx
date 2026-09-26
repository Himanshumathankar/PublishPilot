"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { API_URL, apiRequest } from "@/lib/api";
import type { ArticleBlock, ArticleDocument } from "@/types/article";

type ArticleImage = {
  id: string;
  filename: string;
  caption?: string;
  alt_text?: string;
  source: string;
};
type Article = ArticleDocument & {
  id: string;
  status: string;
  edited_html?: string;
  wordpress_url?: string;
  wordpress_site_id?: string;
  images: ArticleImage[];
};
type Category = { id: number; name: string; parent: number; count: number };
type Author = { id: number; name: string; username: string };
type WordPressSite = {
  id: string;
  name: string;
  base_url: string;
  active: boolean;
};
type ProgressEvent = {
  stage: string;
  status: string;
  message: string;
  timestamp: string;
};
type ProgressResponse = {
  active: boolean;
  success?: boolean;
  error_code?: string;
  error_message?: string;
  events: ProgressEvent[];
};
type ImageAlignment = "left" | "center" | "right" | "none";

function escapeText(value: string) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
function imageFilename(value: string) {
  const slug = value
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  return `${slug || "article-image"}.webp`;
}
function blocksToHtml(article: Article) {
  return article.blocks
    .map((block) => {
      if (block.type === "paragraph") return `<p>${block.html}</p>`;
      if (block.type === "heading")
        return `<h${block.level}>${escapeText(block.text)}</h${block.level}>`;
      if (block.type === "list") {
        const tag = block.ordered ? "ol" : "ul";
        return `<${tag}>${block.items.map((item) => `<li>${item.html}</li>`).join("")}</${tag}>`;
      }
      if (block.type === "table")
        return `<table><tbody>${block.rows.map((row) => `<tr>${row.map((cell) => `<td>${cell.html}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
      return `<figure class="wp-block-image aligncenter"><img data-image-id="${block.image_id}" src="${API_URL}${block.source}" alt="">${block.caption ? `<figcaption class="wp-element-caption">${escapeText(block.caption)}</figcaption>` : ""}</figure>`;
    })
    .join("\n");
}

function Block({ block }: { block: ArticleBlock }) {
  if (block.type === "paragraph")
    return <p dangerouslySetInnerHTML={{ __html: block.html }} />;
  if (block.type === "heading")
    return block.level === 2 ? <h2>{block.text}</h2> : <h3>{block.text}</h3>;
  if (block.type === "list") {
    const Tag = block.ordered ? "ol" : "ul";
    return (
      <Tag>
        {block.items.map((item, i) => (
          <li key={i} dangerouslySetInnerHTML={{ __html: item.html }} />
        ))}
      </Tag>
    );
  }
  if (block.type === "table")
    return (
      <div className="overflow-x-auto">
        <table>
          <tbody>
            {block.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j} dangerouslySetInnerHTML={{ __html: cell.html }} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  return (
    <figure className="text-center">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        className="mx-auto max-h-[650px] max-w-full"
        src={`${API_URL}${block.source}`}
        alt=""
      />
      {block.caption && <figcaption>{block.caption}</figcaption>}
    </figure>
  );
}

function CategoryPicker({
  categories,
  selected,
  onChange,
}: {
  categories: Category[];
  selected: number[];
  onChange: (ids: number[]) => void;
}) {
  const [tab, setTab] = useState<"all" | "used">("all");
  const [search, setSearch] = useState("");
  const toggle = (id: number) =>
    onChange(
      selected.includes(id)
        ? selected.filter((value) => value !== id)
        : [...selected, id],
    );
  const row = (item: Category, depth = 0, includeChildren = true) => (
    <div key={item.id}>
      <label
        className="flex cursor-pointer items-start gap-2 rounded py-1 pr-1 text-sm hover:bg-gray-50"
        style={{ paddingLeft: `${depth * 18 + 4}px` }}
      >
        <input
          type="checkbox"
          className="mt-0.5"
          checked={selected.includes(item.id)}
          onChange={() => toggle(item.id)}
        />
        <span>{item.name}</span>
      </label>
      {includeChildren &&
        categories
          .filter((child) => child.parent === item.id)
          .map((child) => row(child, depth + 1))}
    </div>
  );
  const query = search.trim().toLowerCase();
  const roots = categories.filter(
    (item) =>
      !item.parent ||
      !categories.some((candidate) => candidate.id === item.parent),
  );
  const visible = query
    ? categories.filter((item) => item.name.toLowerCase().includes(query))
    : tab === "used"
      ? [...categories]
          .filter((item) => item.count > 0)
          .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
          .slice(0, 20)
      : roots;
  return (
    <fieldset className="mt-5">
      <legend className="text-sm font-semibold">Categories</legend>
      <input
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        aria-label="Search categories"
        placeholder="Search categories"
        className="mt-2 w-full rounded-lg border p-2 text-sm"
      />
      <div className="mt-2 flex border-b text-sm">
        <button
          type="button"
          onClick={() => setTab("all")}
          className={`border-b-2 px-3 py-2 ${tab === "all" ? "border-[var(--brand)] font-semibold text-[var(--brand)]" : "border-transparent"}`}
        >
          All Categories
        </button>
        <button
          type="button"
          onClick={() => setTab("used")}
          className={`border-b-2 px-3 py-2 ${tab === "used" ? "border-[var(--brand)] font-semibold text-[var(--brand)]" : "border-transparent"}`}
        >
          Most Used
        </button>
      </div>
      <div className="max-h-56 overflow-y-auto rounded-b-lg border border-t-0 p-2">
        {visible.length ? (
          visible.map((item) => row(item, 0, !query && tab === "all"))
        ) : (
          <p className="p-2 text-sm text-[var(--muted)]">
            No categories found.
          </p>
        )}
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">
        {selected.length} selected
      </p>
    </fieldset>
  );
}

export function ArticlePreview({ id }: { id: string }) {
  const [article, setArticle] = useState<Article | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [authors, setAuthors] = useState<Author[]>([]);
  const [sites, setSites] = useState<WordPressSite[]>([]);
  const [siteId, setSiteId] = useState("");
  const [selectedCategories, setSelectedCategories] = useState<number[]>([]);
  const [author, setAuthor] = useState("");
  const [authorSearch, setAuthorSearch] = useState("");
  const [title, setTitle] = useState("");
  const [metaTitle, setMetaTitle] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [slug, setSlug] = useState("");
  const [featured, setFeatured] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [result, setResult] = useState<{
    wordpress_url?: string;
    status: string;
  } | null>(null);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [editingContent, setEditingContent] = useState(false);
  const [editorMode, setEditorMode] = useState<"visual" | "html">("visual");
  const [contentHtml, setContentHtml] = useState("");
  const [imageDrafts, setImageDrafts] = useState<Record<string, ArticleImage>>(
    {},
  );
  const [copied, setCopied] = useState(false);
  const [selectedEditorImageId, setSelectedEditorImageId] = useState("");
  const [editorImageDetails, setEditorImageDetails] = useState({
    alt: "",
    caption: "",
    alignment: "none" as ImageAlignment,
    link: "",
  });
  const editorRef = useRef<HTMLDivElement>(null);
  const selectionRef = useRef<Range | null>(null);

  useEffect(() => {
    apiRequest<Article>(`/articles/${id}`)
      .then((value) => {
        setArticle(value);
        setTitle(value.title);
        setMetaTitle(value.meta_title || "");
        setMetaDescription(value.meta_description || "");
        setExcerpt(value.excerpt || "");
        setSlug(value.slug || "");
        setSiteId(value.wordpress_site_id || "");
        setContentHtml(value.edited_html || blocksToHtml(value));
        setImageDrafts(
          Object.fromEntries(value.images.map((image) => [image.id, image])),
        );
      })
      .catch((e) => setError(e.message));
    apiRequest<{ wordpress_sites: WordPressSite[] }>("/integrations")
      .then((value) => {
        const active = value.wordpress_sites.filter((site) => site.active);
        setSites(active);
        setSiteId((current) => current || active[0]?.id || "");
      })
      .catch((e) => setError(`Settings: ${e.message}`));
  }, [id]);
  useEffect(() => {
    if (!siteId) return;
    let current = true;
    setCategories([]);
    setAuthors([]);
    setSelectedCategories([]);
    setAuthor("");
    setError("");
    const query = `site_id=${encodeURIComponent(siteId)}`;
    apiRequest<Category[]>(`/wordpress/categories?${query}`, {
      cache: "no-store",
    })
      .then((items) => {
        if (current) setCategories(items);
      })
      .catch((e) => {
        if (current) setError(`Categories: ${e.message}`);
      });
    apiRequest<Author[]>(`/wordpress/authors?${query}`, { cache: "no-store" })
      .then((siteAuthors) => {
        if (!current) return;
        setAuthors(siteAuthors);
        if (siteAuthors.length === 1) setAuthor(String(siteAuthors[0].id));
      })
      .catch((e) => {
        if (current) setError(`Authors: ${e.message}`);
      });
    return () => {
      current = false;
    };
  }, [siteId]);

  async function saveMetadata() {
    const editorHtml =
      editingContent && editorMode === "visual"
        ? (editorRef.current?.innerHTML ?? contentHtml)
        : contentHtml;
    const updated = await apiRequest<Article>(`/articles/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        meta_title: metaTitle,
        meta_description: metaDescription,
        excerpt,
        slug,
        content_html:
          editingContent || article?.edited_html ? editorHtml : null,
      }),
    });
    setArticle(updated);
    setSlug(updated.slug || "");
    setContentHtml(updated.edited_html || blocksToHtml(updated));
    setEditingContent(false);
    return updated;
  }

  function rememberSelection() {
    const selection = window.getSelection();
    if (
      selection?.rangeCount &&
      editorRef.current?.contains(selection.anchorNode)
    )
      selectionRef.current = selection.getRangeAt(0).cloneRange();
  }

  function restoreSelection() {
    editorRef.current?.focus();
    if (!selectionRef.current) return;
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(selectionRef.current);
  }

  function selectedFigure() {
    if (selectedEditorImageId) {
      const selected = editorRef.current
        ?.querySelector(
          `img[data-image-id="${CSS.escape(selectedEditorImageId)}"]`,
        )
        ?.closest("figure");
      if (selected) return selected as HTMLElement;
    }
    const range = selectionRef.current;
    if (!range || !editorRef.current) return null;
    let node: Node | null = range.commonAncestorContainer;
    if (node.nodeType === Node.TEXT_NODE) node = node.parentElement;
    let element = node as Element | null;
    if (element?.tagName === "IMG") element = element.parentElement;
    const figure = element?.closest("figure");
    return figure && editorRef.current.contains(figure)
      ? (figure as HTMLElement)
      : null;
  }

  function editorImage() {
    if (!selectedEditorImageId) return null;
    return editorRef.current?.querySelector(
      `img[data-image-id="${CSS.escape(selectedEditorImageId)}"]`,
    ) as HTMLImageElement | null;
  }

  function updateEditorImageDetails(
    field: "alt" | "caption" | "link",
    value: string,
  ) {
    const image = editorImage();
    const figure = image?.closest("figure");
    if (!image || !figure) return;
    if (field === "alt") image.alt = value;
    if (field === "caption") {
      let caption = figure.querySelector("figcaption");
      if (value && !caption) {
        caption = document.createElement("figcaption");
        caption.className = "wp-element-caption";
        figure.appendChild(caption);
      }
      if (caption) {
        caption.textContent = value;
        if (!value) caption.remove();
      }
    }
    if (field === "link") {
      const existingLink = image.closest("a");
      if (!value) {
        if (existingLink) existingLink.replaceWith(image);
      } else if (existingLink) {
        existingLink.href = value;
      } else {
        const link = document.createElement("a");
        link.href = value;
        image.replaceWith(link);
        link.appendChild(image);
      }
    }
    if (field === "alt" || field === "caption") {
      setImageDrafts((current) => {
        const draft = current[selectedEditorImageId];
        if (!draft) return current;
        const genericName = /^image[-_ ]?\d*\.webp$/i.test(draft.filename);
        return {
          ...current,
          [selectedEditorImageId]: {
            ...draft,
            [field === "alt" ? "alt_text" : "caption"]: value,
            filename:
              field === "caption" && value.trim() && genericName
                ? imageFilename(value)
                : draft.filename,
          },
        };
      });
    }
    setEditorImageDetails((current) => ({ ...current, [field]: value }));
    setContentHtml(editorRef.current?.innerHTML ?? contentHtml);
  }

  function alignEditorImage(alignment: ImageAlignment) {
    const image = editorImage();
    const figure = image?.closest("figure");
    if (!image || !figure) return;
    figure.classList.remove(
      "alignleft",
      "aligncenter",
      "alignright",
      "alignnone",
    );
    figure.classList.add(`align${alignment}`);
    figure.style.textAlign = alignment === "none" ? "" : alignment;
    image.style.display = alignment === "center" ? "block" : "inline-block";
    image.style.marginLeft = alignment === "center" ? "auto" : "";
    image.style.marginRight = alignment === "center" ? "auto" : "";
    setEditorImageDetails((current) => ({ ...current, alignment }));
    setContentHtml(editorRef.current?.innerHTML ?? contentHtml);
  }

  function selectEditorImage(target: EventTarget | null) {
    const image = (target as Element | null)?.closest?.(
      "img[data-image-id]",
    ) as HTMLImageElement | null;
    if (!image || !editorRef.current?.contains(image)) return;
    const figure = image.closest("figure");
    const alignment: ImageAlignment = figure?.classList.contains("aligncenter")
      ? "center"
      : figure?.classList.contains("alignright")
        ? "right"
        : figure?.classList.contains("alignleft")
          ? "left"
          : "none";
    setSelectedEditorImageId(image.dataset.imageId || "");
    setEditorImageDetails({
      alt: image.alt || "",
      caption: figure?.querySelector("figcaption")?.textContent || "",
      alignment,
      link: image.closest("a")?.getAttribute("href") || "",
    });
  }

  function editorCommand(command: string, value?: string) {
    restoreSelection();
    if (["justifyLeft", "justifyCenter", "justifyRight"].includes(command)) {
      const figure = selectedFigure();
      if (figure) {
        const alignment =
          command === "justifyCenter"
            ? "center"
            : command === "justifyRight"
              ? "right"
              : "left";
        figure.classList.remove("alignleft", "aligncenter", "alignright");
        figure.classList.add(`align${alignment}`);
        figure.style.textAlign = alignment;
        const image = figure.querySelector("img");
        if (image) {
          image.style.display =
            alignment === "center" ? "block" : "inline-block";
          image.style.marginLeft = alignment === "center" ? "auto" : "";
          image.style.marginRight = alignment === "center" ? "auto" : "";
        }
        rememberSelection();
        return;
      }
    }
    document.execCommand(command, false, value);
    rememberSelection();
  }

  function applyReadmeHighlight() {
    restoreSelection();
    let node: Node | null = window.getSelection()?.anchorNode || null;
    if (node?.nodeType === Node.TEXT_NODE) node = node.parentElement;
    let paragraph = (node as Element | null)?.closest(
      "p",
    ) as HTMLParagraphElement | null;
    if (!paragraph || !editorRef.current?.contains(paragraph)) {
      document.execCommand("formatBlock", false, "p");
      node = window.getSelection()?.anchorNode || null;
      if (node?.nodeType === Node.TEXT_NODE) node = node.parentElement;
      paragraph = (node as Element | null)?.closest(
        "p",
      ) as HTMLParagraphElement | null;
    }
    if (paragraph && editorRef.current?.contains(paragraph)) {
      paragraph.classList.toggle("highlight-also-read");
      rememberSelection();
    }
  }

  function editorKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const modifier = event.metaKey || event.ctrlKey;
    if (event.key === "Tab") {
      event.preventDefault();
      editorCommand(event.shiftKey ? "outdent" : "indent");
      return;
    }
    if (!modifier) return;
    const key = event.key.toLowerCase();
    const commands: Record<string, string> = {
      b: "bold",
      i: "italic",
      u: "underline",
      z: event.shiftKey ? "redo" : "undo",
      y: "redo",
    };
    if (commands[key]) {
      event.preventDefault();
      document.execCommand(commands[key]);
      rememberSelection();
      return;
    }
    if (key === "k") {
      event.preventDefault();
      rememberSelection();
      const url = window.prompt("Link URL");
      if (url) editorCommand("createLink", url);
      return;
    }
    if (key === "s") {
      event.preventDefault();
      setContentHtml(editorRef.current?.innerHTML ?? contentHtml);
      void saveMetadata().catch((reason) => setError(reason.message));
      return;
    }
    if (event.altKey && ["1", "2", "3", "4"].includes(key)) {
      event.preventDefault();
      editorCommand("formatBlock", `h${key}`);
      return;
    }
    if (event.shiftKey && key === "7") {
      event.preventDefault();
      editorCommand("insertOrderedList");
    }
    if (event.shiftKey && key === "8") {
      event.preventDefault();
      editorCommand("insertUnorderedList");
    }
  }

  async function saveImage(imageId: string) {
    const draft = imageDrafts[imageId];
    const updated = await apiRequest<ArticleImage>(
      `/articles/${id}/images/${imageId}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      },
    );
    setImageDrafts((current) => ({
      ...current,
      [imageId]: { ...draft, ...updated },
    }));
    setArticle((current) =>
      current
        ? {
            ...current,
            images: current.images.map((image) =>
              image.id === imageId ? { ...image, ...updated } : image,
            ),
          }
        : current,
    );
  }

  async function saveAllImages() {
    if (!article) return;
    for (const image of article.images) {
      const draft = imageDrafts[image.id] || image;
      await apiRequest<ArticleImage>(`/articles/${id}/images/${image.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
    }
  }

  async function publish(status: "draft" | "publish") {
    if (!siteId || !featured || !selectedCategories.length || !author) {
      setError(
        "Choose a publishing website, at least one category, an author, and a featured image first.",
      );
      return;
    }
    if (
      !title.trim() ||
      !metaTitle.trim() ||
      !metaDescription.trim() ||
      !slug.trim()
    ) {
      setError(
        "Complete the article title, meta title, meta description, and slug first.",
      );
      return;
    }
    setBusy(status);
    setError("");
    const form = new FormData();
    form.append("site_id", siteId);
    selectedCategories.forEach((categoryId) =>
      form.append("category_ids", String(categoryId)),
    );
    form.append("author_id", author);
    form.append("status", status);
    form.append("featured_image", featured);
    let polling = false;
    try {
      await saveAllImages();
      await saveMetadata();
      setProgress([
        {
          stage: "starting",
          status: "working",
          message: "Starting publishing workflow…",
          timestamp: new Date().toISOString(),
        },
      ]);
      polling = true;
      const poll = async () => {
        while (polling) {
          try {
            const state = await apiRequest<ProgressResponse>(
              `/articles/${id}/publish-progress`,
            );
            if (state.events.length) setProgress(state.events);
          } catch {
            /* The publish response reports the actionable error. */
          }
          await new Promise((resolve) => setTimeout(resolve, 700));
        }
      };
      const pollPromise = poll();
      const response = await fetch(`${API_URL}/articles/${id}/publish`, {
        method: "POST",
        body: form,
        credentials: "include",
      });
      const body = await response.json();
      polling = false;
      await pollPromise;
      const finalProgress = await apiRequest<ProgressResponse>(
        `/articles/${id}/publish-progress`,
      ).catch(() => null);
      if (finalProgress?.events.length) setProgress(finalProgress.events);
      if (!response.ok)
        throw new Error(
          `${body?.detail?.code ?? "PUBLISH_ERROR"}: ${body?.detail?.message ?? "Publishing failed."}`,
        );
      setResult(body);
      setArticle((current) =>
        current ? { ...current, wordpress_url: body.wordpress_url } : current,
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Publishing failed.");
    } finally {
      polling = false;
      setBusy("");
    }
  }

  if (!article) return <p className="mt-8">{error || "Loading preview…"}</p>;
  const filteredAuthors = authors.filter((item) =>
    `${item.name} ${item.username}`
      .toLowerCase()
      .includes(authorSearch.toLowerCase()),
  );
  const publishedUrl = result?.wordpress_url || article.wordpress_url;
  return (
    <div className="mt-6 grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_390px]">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm text-[var(--muted)]">Article preview</p>
          {!editingContent && (
            <button
              onClick={() => setEditingContent(true)}
              className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold shadow-sm hover:border-[var(--brand)]"
            >
              Edit content
            </button>
          )}
        </div>
        {editingContent ? (
          <section className="overflow-hidden rounded-2xl border border-[var(--line)] bg-white shadow-sm">
            <div
              className="editor-toolbar border-b bg-gray-50 p-3"
              onMouseDown={(event) => {
                if ((event.target as HTMLElement).closest("button"))
                  event.preventDefault();
              }}
            >
              <div className="flex flex-wrap items-center gap-1.5">
                <select
                  defaultValue="p"
                  onChange={(e) => editorCommand("formatBlock", e.target.value)}
                  className="rounded border bg-white px-2 text-sm"
                  aria-label="Text style"
                >
                  <option value="p">Paragraph</option>
                  <option value="h1">Heading 1</option>
                  <option value="h2">Heading 2</option>
                  <option value="h3">Heading 3</option>
                  <option value="h4">Heading 4</option>
                  <option value="blockquote">Quote</option>
                </select>
                <select
                  defaultValue="Arial"
                  onChange={(e) => editorCommand("fontName", e.target.value)}
                  className="rounded border bg-white px-2 text-sm"
                  aria-label="Font"
                >
                  <option>Arial</option>
                  <option>Georgia</option>
                  <option>Times New Roman</option>
                  <option>Verdana</option>
                </select>
                <select
                  defaultValue="3"
                  onChange={(e) => editorCommand("fontSize", e.target.value)}
                  className="rounded border bg-white px-2 text-sm"
                  aria-label="Text size"
                >
                  <option value="2">Small</option>
                  <option value="3">Normal</option>
                  <option value="4">Large</option>
                  <option value="5">Extra large</option>
                </select>
                <button
                  onClick={() => editorCommand("undo")}
                  className="rounded border bg-white px-2"
                  title="Undo"
                >
                  ↶
                </button>
                <button
                  onClick={() => editorCommand("redo")}
                  className="rounded border bg-white px-2"
                  title="Redo"
                >
                  ↷
                </button>
                <button
                  onClick={() => editorCommand("bold")}
                  className="rounded border bg-white px-2 font-bold"
                  title="Bold"
                >
                  B
                </button>
                <button
                  onClick={() => editorCommand("italic")}
                  className="rounded border bg-white px-2 italic"
                  title="Italic"
                >
                  I
                </button>
                <button
                  onClick={() => editorCommand("underline")}
                  className="rounded border bg-white px-2 underline"
                  title="Underline"
                >
                  U
                </button>
                <button
                  onClick={() => editorCommand("strikeThrough")}
                  className="rounded border bg-white px-2 line-through"
                  title="Strikethrough"
                >
                  S
                </button>
                <button
                  onClick={() => editorCommand("insertUnorderedList")}
                  className="rounded border bg-white px-2"
                  title="Bulleted list"
                >
                  • List
                </button>
                <button
                  onClick={() => editorCommand("insertOrderedList")}
                  className="rounded border bg-white px-2"
                  title="Numbered list"
                >
                  1. List
                </button>
                <button
                  onClick={() => editorCommand("outdent")}
                  className="rounded border bg-white px-2"
                  title="Outdent"
                >
                  ⇤
                </button>
                <button
                  onClick={() => editorCommand("indent")}
                  className="rounded border bg-white px-2"
                  title="Indent"
                >
                  ⇥
                </button>
                <button
                  onClick={() => editorCommand("justifyLeft")}
                  className="rounded border bg-white px-2"
                  title="Align left"
                >
                  ≡
                </button>
                <button
                  onClick={() => editorCommand("justifyCenter")}
                  className="rounded border bg-white px-2"
                  title="Align centre"
                >
                  ≣
                </button>
                <button
                  onClick={() => editorCommand("justifyRight")}
                  className="rounded border bg-white px-2"
                  title="Align right"
                >
                  ≡→
                </button>
                <label
                  className="flex items-center gap-1 rounded border bg-white px-2 text-xs"
                  title="Text colour"
                >
                  A
                  <input
                    type="color"
                    className="h-6 w-5"
                    onChange={(e) => editorCommand("foreColor", e.target.value)}
                  />
                </label>
                <label
                  className="flex items-center gap-1 rounded border bg-white px-2 text-xs"
                  title="Highlight colour"
                >
                  ▰
                  <input
                    type="color"
                    className="h-6 w-5"
                    onChange={(e) =>
                      editorCommand("hiliteColor", e.target.value)
                    }
                  />
                </label>
                <button
                  onClick={() => {
                    const url = window.prompt("Link URL");
                    if (url) editorCommand("createLink", url);
                  }}
                  className="rounded border bg-white px-2"
                  title="Insert link"
                >
                  Link
                </button>
                <button
                  onClick={() => editorCommand("unlink")}
                  className="rounded border bg-white px-2"
                  title="Remove link"
                >
                  Unlink
                </button>
                <button
                  onClick={() => editorCommand("insertHorizontalRule")}
                  className="rounded border bg-white px-2"
                  title="Horizontal line"
                >
                  —
                </button>
                <button
                  onClick={() => editorCommand("removeFormat")}
                  className="rounded border bg-white px-2"
                  title="Clear formatting"
                >
                  Clear
                </button>
                <button
                  onClick={applyReadmeHighlight}
                  className="rounded border-2 border-black bg-[#f7f2f0] px-2 font-semibold"
                  title="Apply or remove the highlight-also-read paragraph style"
                >
                  Readme highlight
                </button>
                <div className="ml-auto flex text-xs">
                  <button
                    onClick={() => {
                      setContentHtml(
                        editorRef.current?.innerHTML ?? contentHtml,
                      );
                      setEditorMode("visual");
                    }}
                    className={`rounded-l border px-2 ${editorMode === "visual" ? "bg-[var(--brand)] text-white" : "bg-white"}`}
                  >
                    Visual
                  </button>
                  <button
                    onClick={() => {
                      setContentHtml(
                        editorRef.current?.innerHTML ?? contentHtml,
                      );
                      setEditorMode("html");
                    }}
                    className={`rounded-r border px-2 ${editorMode === "html" ? "bg-[var(--brand)] text-white" : "bg-white"}`}
                  >
                    HTML
                  </button>
                </div>
              </div>
              <p className="mt-2 text-xs text-[var(--muted)]">
                Shortcuts: ⌘/Ctrl+B bold · I italic · U underline · Z undo · Y
                or ⇧Z redo · K link · S save · ⌥1–4 headings · ⇧7/8 lists · Tab
                indent
              </p>
            </div>
            {editorMode === "visual" && selectedEditorImageId && (
              <section className="border-b bg-white p-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold">Image details</h3>
                  <button
                    type="button"
                    onClick={() => setSelectedEditorImageId("")}
                    className="text-sm text-[var(--muted)]"
                  >
                    Close
                  </button>
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <label className="text-sm font-semibold">
                    Alternative Text
                    <textarea
                      value={editorImageDetails.alt}
                      onChange={(event) =>
                        updateEditorImageDetails("alt", event.target.value)
                      }
                      rows={2}
                      className="mt-1 w-full rounded border p-2 font-normal"
                    />
                  </label>
                  <label className="text-sm font-semibold">
                    Caption
                    <textarea
                      value={editorImageDetails.caption}
                      onChange={(event) =>
                        updateEditorImageDetails("caption", event.target.value)
                      }
                      rows={2}
                      className="mt-1 w-full rounded border p-2 font-normal"
                    />
                  </label>
                  <fieldset>
                    <legend className="text-sm font-semibold">Align</legend>
                    <div className="mt-1 inline-flex">
                      {(
                        ["left", "center", "right", "none"] as ImageAlignment[]
                      ).map((alignment) => (
                        <button
                          key={alignment}
                          type="button"
                          onClick={() => alignEditorImage(alignment)}
                          className={`border px-4 py-2 text-sm capitalize first:rounded-l last:rounded-r ${editorImageDetails.alignment === alignment ? "bg-[var(--brand)] text-white" : "bg-white"}`}
                        >
                          {alignment}
                        </button>
                      ))}
                    </div>
                  </fieldset>
                  <label className="text-sm font-semibold">
                    Link to
                    <input
                      type="url"
                      value={editorImageDetails.link}
                      onChange={(event) =>
                        updateEditorImageDetails("link", event.target.value)
                      }
                      placeholder="None — or enter https://…"
                      className="mt-1 w-full rounded border p-2 font-normal"
                    />
                  </label>
                </div>
              </section>
            )}
            {editorMode === "visual" ? (
              <div
                ref={editorRef}
                contentEditable
                suppressContentEditableWarning
                onClick={(event) => selectEditorImage(event.target)}
                onKeyDown={editorKeyDown}
                onKeyUp={rememberSelection}
                onMouseUp={rememberSelection}
                onInput={rememberSelection}
                dangerouslySetInnerHTML={{ __html: contentHtml }}
                className="article-preview min-h-[700px] p-6 outline-none sm:p-10"
              />
            ) : (
              <textarea
                value={contentHtml}
                onChange={(e) => setContentHtml(e.target.value)}
                className="min-h-[700px] w-full resize-y p-5 font-mono text-sm outline-none"
                spellCheck={false}
              />
            )}
            <div className="flex justify-end gap-2 border-t bg-gray-50 p-3">
              <button
                onClick={() => {
                  setContentHtml(article.edited_html || blocksToHtml(article));
                  setEditingContent(false);
                  setSelectedEditorImageId("");
                }}
                className="rounded-lg border bg-white px-4 py-2 text-sm font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  saveMetadata().catch((reason) => setError(reason.message))
                }
                className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-semibold text-white"
              >
                Save content
              </button>
            </div>
          </section>
        ) : (
          <article className="article-preview mx-auto min-h-[700px] max-w-[900px] rounded-2xl border border-[var(--line)] bg-white p-6 shadow-sm sm:p-12">
            <h1>{title || article.title}</h1>
            {article.edited_html ? (
              <div dangerouslySetInnerHTML={{ __html: article.edited_html }} />
            ) : (
              article.blocks.map((block, i) => <Block block={block} key={i} />)
            )}
          </article>
        )}
      </div>
      <aside className="lg:sticky lg:top-4">
        <section className="rounded-2xl border border-[var(--line)] bg-white p-5 shadow-sm">
          <h2 className="text-lg font-bold">Publishing details</h2>
          <div className="mt-4 space-y-3 text-sm">
            <label className="block font-semibold">
              Article title
              <input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full rounded-lg border p-2 font-normal"
              />
            </label>
            <label className="block font-semibold">
              Meta title
              <textarea
                value={metaTitle}
                onChange={(e) => setMetaTitle(e.target.value)}
                rows={3}
                className="mt-1 w-full rounded-lg border p-2 font-normal"
              />
            </label>
            <label className="block font-semibold">
              Meta description
              <textarea
                value={metaDescription}
                onChange={(e) => setMetaDescription(e.target.value)}
                rows={4}
                className="mt-1 w-full rounded-lg border p-2 font-normal"
              />
            </label>
            <label className="block font-semibold">
              Excerpt
              <textarea
                value={excerpt}
                onChange={(e) => setExcerpt(e.target.value)}
                rows={4}
                placeholder="Short summary shown by WordPress themes, archives, and search results"
                className="mt-1 w-full rounded-lg border p-2 font-normal"
              />
              <span className="mt-1 block text-xs font-normal text-[var(--muted)]">
                {excerpt.length} characters
              </span>
            </label>
            <label className="block font-semibold">
              URL slug
              <input
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                className="mt-1 w-full rounded-lg border p-2 font-normal"
              />
            </label>
            <div>
              <span className="font-semibold">Inline images</span>
              <p className="text-[var(--muted)]">
                {article.images.length} · converted to WebP
              </p>
              <div className="mt-2 space-y-2">
                {article.images.map((image, index) => {
                  const draft = imageDrafts[image.id] || image;
                  return (
                    <details
                      key={image.id}
                      className="rounded-lg border bg-gray-50 p-3"
                    >
                      <summary className="cursor-pointer font-semibold">
                        Image {index + 1}:{" "}
                        <span className="font-normal text-[var(--muted)]">
                          {draft.filename}
                        </span>
                      </summary>
                      <div className="mt-3 space-y-3">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={`${API_URL}${image.source}`}
                          alt={draft.alt_text || ""}
                          className="max-h-36 w-full rounded-lg bg-white object-contain"
                        />
                        <label className="block font-semibold">
                          WebP filename
                          <input
                            value={draft.filename}
                            onChange={(e) =>
                              setImageDrafts((current) => ({
                                ...current,
                                [image.id]: {
                                  ...draft,
                                  filename: e.target.value,
                                },
                              }))
                            }
                            className="mt-1 w-full rounded-md border bg-white p-2 font-normal"
                          />
                        </label>
                        <label className="block font-semibold">
                          Caption
                          <textarea
                            value={draft.caption || ""}
                            onChange={(e) =>
                              setImageDrafts((current) => ({
                                ...current,
                                [image.id]: {
                                  ...draft,
                                  caption: e.target.value,
                                  filename:
                                    e.target.value.trim() &&
                                    /^image[-_ ]?\d*\.webp$/i.test(
                                      draft.filename,
                                    )
                                      ? imageFilename(e.target.value)
                                      : draft.filename,
                                },
                              }))
                            }
                            rows={2}
                            className="mt-1 w-full rounded-md border bg-white p-2 font-normal"
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() =>
                            setImageDrafts((current) => ({
                              ...current,
                              [image.id]: {
                                ...draft,
                                filename: imageFilename(
                                  draft.caption ||
                                    draft.alt_text ||
                                    `article-image-${index + 1}`,
                                ),
                              },
                            }))
                          }
                          className="text-xs font-semibold text-[var(--brand)] underline"
                        >
                          Use caption as filename
                        </button>
                        <label className="block font-semibold">
                          Alternative text
                          <input
                            value={draft.alt_text || ""}
                            onChange={(e) =>
                              setImageDrafts((current) => ({
                                ...current,
                                [image.id]: {
                                  ...draft,
                                  alt_text: e.target.value,
                                },
                              }))
                            }
                            className="mt-1 w-full rounded-md border bg-white p-2 font-normal"
                          />
                        </label>
                        <button
                          type="button"
                          onClick={() =>
                            saveImage(image.id)
                              .then(() =>
                                setResult({
                                  status: `image ${index + 1} updated`,
                                }),
                              )
                              .catch((reason) => setError(reason.message))
                          }
                          className="w-full rounded-md border bg-white px-3 py-2 font-semibold"
                        >
                          Save image details
                        </button>
                      </div>
                    </details>
                  );
                })}
              </div>
            </div>
          </div>
          <fieldset className="mt-5">
            <legend className="text-sm font-semibold">
              Publish to website
            </legend>
            <div className="mt-2 space-y-1 rounded-lg border p-2">
              {sites.length ? (
                sites.map((site) => (
                  <label
                    key={site.id}
                    className="flex cursor-pointer gap-2 rounded px-1 py-2 text-sm hover:bg-gray-50"
                  >
                    <input
                      type="radio"
                      name="wordpress-site"
                      checked={siteId === site.id}
                      onChange={() => setSiteId(site.id)}
                    />
                    <span>
                      <strong>{site.name}</strong>
                      <span className="block text-xs text-[var(--muted)]">
                        {site.base_url}
                      </span>
                    </span>
                  </label>
                ))
              ) : (
                <p className="p-2 text-sm text-red-700">
                  No website configured. Add one in Settings.
                </p>
              )}
            </div>
          </fieldset>
          <CategoryPicker
            categories={categories}
            selected={selectedCategories}
            onChange={setSelectedCategories}
          />
          <fieldset className="mt-5">
            <legend className="text-sm font-semibold">Author</legend>
            <input
              value={authorSearch}
              onChange={(e) => setAuthorSearch(e.target.value)}
              aria-label="Search authors"
              placeholder="Search display name or username"
              className="mt-2 w-full rounded-lg border p-2 text-sm"
            />
            <div className="mt-2 max-h-52 overflow-y-auto rounded-lg border p-2">
              {filteredAuthors.length ? (
                filteredAuthors.map((item) => (
                  <label
                    key={item.id}
                    className="flex cursor-pointer items-start gap-2 rounded px-1 py-1.5 text-sm hover:bg-gray-50"
                  >
                    <input
                      className="mt-0.5"
                      type="radio"
                      name="wordpress-author"
                      checked={author === String(item.id)}
                      onChange={() => setAuthor(String(item.id))}
                    />
                    <span>
                      <span className="block font-medium">{item.name}</span>
                      {item.username && (
                        <span className="block text-xs text-[var(--muted)]">
                          @{item.username}
                        </span>
                      )}
                    </span>
                  </label>
                ))
              ) : (
                <p className="p-1 text-sm text-[var(--muted)]">
                  No authors found.
                </p>
              )}
            </div>
            <p className="mt-1 text-xs text-[var(--muted)]">
              {author
                ? (() => {
                    const selected = authors.find(
                      (item) => String(item.id) === author,
                    );
                    return selected
                      ? `${selected.name}${selected.username ? ` (@${selected.username})` : ""}`
                      : "1 selected";
                  })()
                : "No author selected"}
            </p>
          </fieldset>
          <label className="mt-4 block text-sm font-semibold">
            Featured image
            <input
              className="mt-2 block w-full text-xs"
              type="file"
              accept="image/*"
              onChange={(e) => setFeatured(e.target.files?.[0] ?? null)}
            />
          </label>
          {error && (
            <p
              role="alert"
              className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700"
            >
              {error}
            </p>
          )}
          {result && (
            <p className="mt-4 text-sm font-semibold text-green-700">
              Saved as {result.status}.
            </p>
          )}
          {publishedUrl && (
            <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3">
              <p className="text-xs font-bold uppercase tracking-wide text-green-800">
                WordPress post link
              </p>
              <div className="mt-2 flex gap-2">
                <input
                  readOnly
                  value={publishedUrl}
                  className="min-w-0 flex-1 rounded-md border bg-white p-2 text-xs"
                />
                <button
                  type="button"
                  onClick={async () => {
                    await navigator.clipboard.writeText(publishedUrl);
                    setCopied(true);
                    window.setTimeout(() => setCopied(false), 1800);
                  }}
                  className="rounded-md bg-[var(--brand)] px-3 text-sm font-semibold text-white"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <a
                href={publishedUrl}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block text-sm font-semibold text-[var(--brand)] underline"
              >
                Open in WordPress ↗
              </a>
            </div>
          )}
          {progress.length > 0 && (
            <div className="mt-5 rounded-lg border border-[var(--line)] bg-gray-50 p-3">
              <h3 className="text-sm font-bold">Publishing progress</h3>
              <ol className="mt-2 space-y-2">
                {progress.map((event, index) => (
                  <li
                    key={`${event.timestamp}-${index}`}
                    className="flex gap-2 text-xs"
                  >
                    <span aria-hidden="true">
                      {event.status === "failed"
                        ? "✕"
                        : event.status === "working"
                          ? "●"
                          : event.status === "reused"
                            ? "↺"
                            : "✓"}
                    </span>
                    <span
                      className={
                        event.status === "failed"
                          ? "text-red-700"
                          : "text-[var(--muted)]"
                      }
                    >
                      {event.message}
                    </span>
                  </li>
                ))}
              </ol>
            </div>
          )}
          <div className="mt-5 grid gap-2">
            <button
              disabled={!!busy}
              onClick={() =>
                saveMetadata()
                  .then(() => setResult({ status: "changes" }))
                  .catch((reason) => setError(reason.message))
              }
              className="rounded-lg border px-4 py-2 font-semibold"
            >
              Save changes
            </button>
            <button
              disabled={!!busy}
              onClick={() => publish("draft")}
              className="rounded-lg border px-4 py-2 font-semibold"
            >
              {busy === "draft" ? "Saving…" : "Save as draft"}
            </button>
            <button
              disabled={!!busy}
              onClick={() => publish("publish")}
              className="rounded-lg bg-[var(--brand)] px-4 py-2 font-semibold text-white"
            >
              {busy === "publish" ? "Publishing…" : "Publish"}
            </button>
          </div>
        </section>
      </aside>
    </div>
  );
}
