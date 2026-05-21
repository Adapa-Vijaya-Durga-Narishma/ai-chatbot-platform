import type { Attachment } from "./attachment";

export interface PdfUploadResponse {
  thread_id: string;
  attachment: Attachment;
  chunks_indexed: number;
  status: "ready" | "uploaded_no_text";
}
