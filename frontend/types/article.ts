export type ArticleBlock =
  | { type: "paragraph"; html: string }
  | { type: "heading"; level: 2 | 3; text: string }
  | { type: "list"; ordered: boolean; items: { html: string }[] }
  | { type: "image"; image_id: string; source: string; caption?: string; figure_number?: number; filename?: string }
  | { type: "table"; rows: { html: string }[][] };

export interface ArticleDocument {
  title: string;
  meta_title?: string;
  meta_description?: string;
  excerpt?: string;
  slug?: string;
  blocks: ArticleBlock[];
}
