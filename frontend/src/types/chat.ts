/**
 * Chat message types — shared across components.
 * Always import types from here, never inline.
 */

import type { Attachment } from "./attachment";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  attachments: Attachment[];
  isGenerating?: boolean;
}

export interface ChatRequest {
  message: string;
  thread_id?: string;
  attachment_ids?: string[];
  mode?: "normal" | "upload" | "upload-pdf" | "generate-image";
}

export interface ChatResponse {
  content: string;
  finished: boolean;
}

export interface ChatThread {
  id: string;
  title: string | null;
  created_at: string;
}

export interface ChatThreadResponse {
  id: string;
  title: string | null;
  created_at: string;
}

export interface ChatMessageResponse {
  id: string;
  thread_id: string;
  role: string;
  content: string;
  created_at: string;
  attachments: Attachment[];
}
