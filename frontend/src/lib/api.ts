import axios from "axios";
import type { ChatRequest, ChatThreadResponse, ChatMessageResponse } from "../types/chat";
import type { Attachment, AttachmentUploadResponse } from "../types/attachment";
import type {
  DataframeQueryResponse,
  DataframeSourceResponse,
  GoogleSheetConnectRequest,
} from "../types/dataframe";
import type { PdfUploadResponse } from "../types/rag";
import type { ResearchDigestRequest, ResearchStreamEvent } from "../types/research";
import type { SqlQueryResponse } from "../types/sql";
import type { User, UserCreate, UserLogin } from "../types/user";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const message =
      typeof detail === "object" && detail?.message
        ? detail.message
        : error.message;
    return Promise.reject(new Error(message));
  }
);

export async function register(data: UserCreate): Promise<User> {
  const res = await apiClient.post<User>("/api/auth/register", data);
  return res.data;
}

export async function login(data: UserLogin): Promise<User> {
  const res = await apiClient.post<User>("/api/auth/login", data);
  return res.data;
}

export async function logout(): Promise<void> {
  await apiClient.post("/api/auth/logout");
}

export async function getMe(): Promise<User> {
  const res = await apiClient.get<User>("/api/auth/me");
  return res.data;
}

export async function getThreads(): Promise<ChatThreadResponse[]> {
  const res = await apiClient.get<ChatThreadResponse[]>("/api/chat/threads");
  return res.data;
}

export async function createThread(title?: string): Promise<ChatThreadResponse> {
  const res = await apiClient.post<ChatThreadResponse>("/api/chat/threads", {
    title: title ?? null,
  });
  return res.data;
}

export async function renameThread(
  threadId: string,
  title: string
): Promise<ChatThreadResponse> {
  const res = await apiClient.patch<ChatThreadResponse>(
    `/api/chat/threads/${threadId}`,
    { title }
  );
  return res.data;
}

export async function deleteThread(threadId: string): Promise<void> {
  await apiClient.delete(`/api/chat/threads/${threadId}`);
}

export async function getMessages(threadId: string): Promise<ChatMessageResponse[]> {
  const res = await apiClient.get<ChatMessageResponse[]>(
    `/api/chat/threads/${threadId}/messages`
  );
  return res.data;
}

export async function sendChatMessage(
  message: string,
  onToken: (token: string) => void,
  threadId?: string,
  attachmentIds?: string[],
  mode: "normal" | "upload" | "upload-pdf" | "generate-image" = "normal"
): Promise<string | undefined> {
  const payload: ChatRequest = {
    message,
    thread_id: threadId,
    attachment_ids: attachmentIds,
    mode,
  };

  const response = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to send message");
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let returnedThreadId: string | undefined;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const threadMatch = buffer.match(/data:\s*\{"thread_id":\s*"([^"]+)"\}/);
      if (threadMatch) {
        returnedThreadId = threadMatch[1];
        buffer = buffer.replace(/\n\ndata:\s*\{.*\}/, "");
      }

      if (buffer) {
        onToken(buffer);
        buffer = "";
      }
    }
  } finally {
    reader.releaseLock();
  }

  return returnedThreadId;
}

export function isImageGenerationPrompt(message: string): boolean {
  const text = message.trim();
  if (!text) return false;

  const patterns = [
    /\bgenerate\b.*\bimage\b/i,
    /\bcreate\b.*\bimage\b/i,
    /\bmake\b.*\bimage\b/i,
    /\bdraw\b/i,
  ];

  return patterns.some((pattern) => pattern.test(text));
}

interface ImageGenerationChatResponse {
  thread_id: string;
  message: ChatMessageResponse;
}

export async function sendImageGenerationMessage(
  message: string,
  threadId?: string,
  attachmentIds?: string[]
): Promise<ImageGenerationChatResponse> {
  const payload: ChatRequest = {
    message,
    thread_id: threadId,
    attachment_ids: attachmentIds,
    mode: "generate-image",
  };

  const res = await apiClient.post<ImageGenerationChatResponse>("/api/chat", payload, {
    timeout: 95000,
  });
  return res.data;
}

export async function uploadAttachments(
  files: File[],
  onProgress?: (percentage: number) => void
): Promise<Attachment[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));

  const res = await apiClient.post<AttachmentUploadResponse>("/api/chat/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      const percentage = Math.round((event.loaded * 100) / event.total);
      onProgress(percentage);
    },
  });

  return res.data.attachments;
}

export async function sendMessageWithAttachments(
  message: string,
  files: File[],
  onToken: (token: string) => void,
  threadId?: string,
  onUploadProgress?: (percentage: number) => void
): Promise<{ threadId?: string; attachments: Attachment[] }> {
  const attachments = files.length ? await uploadAttachments(files, onUploadProgress) : [];
  const attachmentIds = attachments.map((attachment) => attachment.id);
  const createdThreadId = await sendChatMessage(message, onToken, threadId, attachmentIds);
  return { threadId: createdThreadId, attachments };
}

export async function uploadPdf(
  file: File,
  threadId?: string,
  onProgress?: (percentage: number) => void
): Promise<PdfUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (threadId) {
    formData.append("thread_id", threadId);
  }

  const res = await apiClient.post<PdfUploadResponse>("/api/chat/upload-pdf", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (event) => {
      if (!event.total || !onProgress) return;
      const percentage = Math.round((event.loaded * 100) / event.total);
      onProgress(percentage);
    },
  });

  return res.data;
}

export async function askPdfQuestion(
  message: string,
  onToken: (token: string) => void,
  threadId: string
): Promise<string | undefined> {
  return sendChatMessage(message, onToken, threadId, undefined, "upload-pdf");
}

export function getGoogleLoginUrl(): string {
  return `${BASE_URL}/api/auth/google/login`;
}

export async function askSqlQuestion(question: string, threadId?: string): Promise<SqlQueryResponse> {
  const res = await apiClient.post<SqlQueryResponse>("/api/sql-chat/query", { 
    question,
    thread_id: threadId
  });
  return res.data;
}

export async function uploadDataframeFile(file: File): Promise<DataframeSourceResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await apiClient.post<DataframeSourceResponse>("/api/dataframe-chat/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return res.data;
}

export async function connectGoogleSheet(
  payload: GoogleSheetConnectRequest
): Promise<DataframeSourceResponse> {
  const res = await apiClient.post<DataframeSourceResponse>("/api/dataframe-chat/google-sheet", payload);
  return res.data;
}

export async function askDataframeQuestion(question: string): Promise<DataframeQueryResponse> {
  const res = await apiClient.post<DataframeQueryResponse>("/api/dataframe-chat/query", { question });
  return res.data;
}

function parseSseChunk(chunk: string): ResearchStreamEvent[] {
  const blocks = chunk.split("\n\n");
  const events: ResearchStreamEvent[] = [];

  for (const block of blocks) {
    if (!block.trim()) {
      continue;
    }
    const payload = block
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trim())
      .join("\n");

    if (!payload) {
      continue;
    }

    try {
      const parsed = JSON.parse(payload) as ResearchStreamEvent;
      events.push(parsed);
    } catch {
      // Ignore malformed stream entries and continue parsing subsequent events.
    }
  }

  return events;
}

export async function startResearchDigest(
  topic: string,
  onEvent: (event: ResearchStreamEvent) => void,
  threadId?: string
): Promise<void> {
  const payload: ResearchDigestRequest = {
    topic,
    thread_id: threadId,
  };

  const response = await fetch(`${BASE_URL}/api/research/research-digest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.message || "Failed to start research digest");
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        if (buffer.trim()) {
          const remainingEvents = parseSseChunk(buffer + "\n\n");
          remainingEvents.forEach(onEvent);
        }
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      let boundary = buffer.indexOf("\n\n");
      while (boundary !== -1) {
        const chunk = buffer.slice(0, boundary + 2);
        buffer = buffer.slice(boundary + 2);

        const events = parseSseChunk(chunk);
        events.forEach(onEvent);

        boundary = buffer.indexOf("\n\n");
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// ── Tic Tac Toe API ──────────────────────────────────────────────────────────

import type { TicTacToeGame, MoveResponse, PlayerMoveRequest } from "../types/tic-tac-toe";

export async function createTicTacToeGame(): Promise<TicTacToeGame> {
  const res = await apiClient.post<TicTacToeGame>("/api/tic-tac-toe/new-game");
  return res.data;
}

export async function makeTicTacToeMove(
  gameId: string,
  row: number,
  col: number
): Promise<MoveResponse> {
  const payload: PlayerMoveRequest = { game_id: gameId, row, col };
  const res = await apiClient.post<MoveResponse>("/api/tic-tac-toe/move", payload);
  return res.data;
}

export async function getTicTacToeGame(gameId: string): Promise<TicTacToeGame> {
  const res = await apiClient.get<TicTacToeGame>(`/api/tic-tac-toe/${gameId}`);
  return res.data;
}

export async function restartTicTacToeGame(gameId: string): Promise<TicTacToeGame> {
  const res = await apiClient.post<TicTacToeGame>(`/api/tic-tac-toe/${gameId}/restart`);
  return res.data;
}

export async function listTicTacToeGames(includeCompleted = true): Promise<TicTacToeGame[]> {
  const res = await apiClient.get<TicTacToeGame[]>("/api/tic-tac-toe", {
    params: { include_completed: includeCompleted },
  });
  return res.data;
}