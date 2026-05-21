export type AttachmentType =
  | "image"
  | "generated_image"
  | "video"
  | "pdf"
  | "code"
  | "text"
  | "csv"
  | "formula"
  | "other";

export interface Attachment {
  id: string;
  message_id: string | null;
  original_filename: string;
  stored_filename: string;
  file_path: string;
  mime_type: string;
  file_size: number;
  attachment_type: AttachmentType;
  created_at: string;
}

export interface AttachmentUploadResponse {
  attachments: Attachment[];
}
