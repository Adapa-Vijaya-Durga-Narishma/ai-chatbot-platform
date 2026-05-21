import { useEffect, useRef, useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { useMutation } from "@tanstack/react-query";
import {
  getMessages,
  askPdfQuestion,
  sendChatMessage,
  sendImageGenerationMessage,
  uploadPdf,
  uploadAttachments,
  askSqlQuestion,
} from "../../lib/api";
import type { Attachment } from "../../types/attachment";
import type { ChatMessage as IChatMessage } from "../../types/chat";
import type { SqlQueryResponse } from "../../types/sql";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
import { SqlResultModal } from "./SqlResultModal";

interface Props {
  threadId: string | null;
  onThreadCreated: (id: string) => void;
}

export function ChatWindow({ threadId, onThreadCreated }: Props) {
  const [messages, setMessages] = useState<IChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isGeneratingImage, setIsGeneratingImage] = useState(false);
  const [isProcessingPdf, setIsProcessingPdf] = useState(false);
  const [pdfStatus, setPdfStatus] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [sqlResult, setSqlResult] = useState<SqlQueryResponse | null>(null);
  const [sqlModalOpen, setSqlModalOpen] = useState(false);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const activeThreadRef = useRef<string | null>(threadId);
  const activeStreamAssistantIdRef = useRef<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => uploadAttachments(files, setUploadProgress),
  });

  const mapMessages = useCallback((msgs: Awaited<ReturnType<typeof getMessages>>) => {
    return msgs.map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant",
      content: m.content,
      timestamp: new Date(m.created_at),
      attachments: m.attachments ?? [],
    }));
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load messages when thread changes
  useEffect(() => {
    activeThreadRef.current = threadId;
    if (!threadId) {
      setMessages([]);
      return;
    }
    setIsLoading(true);
    getMessages(threadId)
      .then((msgs) => {
        if (activeThreadRef.current !== threadId) return;
        setMessages(mapMessages(msgs));
      })
      .catch(() => setError("Failed to load messages"))
      .finally(() => setIsLoading(false));
  }, [threadId, mapMessages]);

  const handleSendMessage = useCallback(
    async (
      userMessage: string,
      files: File[],
      mode: "normal" | "upload" | "upload-pdf" | "generate-image" | "database-query"
    ) => {
      setError(null);
      setUploadProgress(0);
      setPdfStatus(null);

      const trimmedQuestion = userMessage.trim();
      if (!trimmedQuestion && files.length === 0) {
        return;
      }

      setIsLoading(true);

      let uploadedAttachments: Attachment[] = [];
      let activeThreadIdForRequest = threadId ?? undefined;

      const pdfFiles = files.filter(
        (file) => file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
      );

      if (pdfFiles.length > 0) {

        if (!pdfFiles.length) {
          setError("Please select at least one PDF file.");
          setIsLoading(false);
          return;
        }

        try {
          for (const file of pdfFiles) {
            setPdfStatus("Uploading...");
            const uploadResult = await uploadPdf(
              file,
              activeThreadIdForRequest,
              (percentage) => {
                setUploadProgress(percentage);
                if (percentage >= 100) {
                  setIsProcessingPdf(true);
                  setPdfStatus("Processing PDF...");
                }
              }
            );
            activeThreadIdForRequest = uploadResult.thread_id;
            uploadedAttachments = [...uploadedAttachments, uploadResult.attachment];
          }

          if (activeThreadIdForRequest && activeThreadIdForRequest !== threadId) {
            onThreadCreated(activeThreadIdForRequest);
          }

          if (activeThreadIdForRequest) {
            const refreshed = await getMessages(activeThreadIdForRequest);
            setMessages(mapMessages(refreshed));
          }

          setPdfStatus("Ready for questions");
          setIsProcessingPdf(false);
          setUploadProgress(0);

          if (!userMessage.trim()) {
            setIsLoading(false);
            return;
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Failed to upload PDF";
          setError(msg);
          setIsLoading(false);
          setIsProcessingPdf(false);
          setPdfStatus(null);
          setUploadProgress(0);
          return;
        }
      }

      const nonPdfFiles = files.filter(
        (file) => !(file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf"))
      );
      if (nonPdfFiles.length > 0) {
        try {
          if (nonPdfFiles.length > 0) {
            uploadedAttachments = await uploadMutation.mutateAsync(nonPdfFiles);
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Failed to upload attachments";
          setError(msg);
          setIsLoading(false);
          return;
        }
      }

      const userMessageId = uuidv4();
      const userMsg: IChatMessage = {
        id: userMessageId,
        role: "user",
        content: userMessage,
        timestamp: new Date(),
        attachments: uploadedAttachments,
      };
      setMessages((prev) => [...prev, userMsg]);

      const assistantId = uuidv4();
      activeStreamAssistantIdRef.current = assistantId;
      const isImageMode = mode === "generate-image";
      setIsGeneratingImage(isImageMode);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: "assistant",
          content: isImageMode ? "Generating image..." : "",
          timestamp: new Date(),
          attachments: [],
          isGenerating: isImageMode,
        },
      ]);

      try {
        if (isImageMode) {
          const imageResponse = await sendImageGenerationMessage(
            userMessage,
            activeThreadIdForRequest,
            uploadedAttachments.map((attachment) => attachment.id)
          );

          if (imageResponse.thread_id && imageResponse.thread_id !== threadId) {
            onThreadCreated(imageResponse.thread_id);
          }

          setMessages((prev) => {
            const updated = [...prev];
            const targetIndex = updated.findIndex((message) => message.id === assistantId);
            if (targetIndex === -1) {
              return updated;
            }

            updated[targetIndex] = {
              id: imageResponse.message.id,
              role: "assistant",
              content: imageResponse.message.content,
              timestamp: new Date(imageResponse.message.created_at),
              attachments: imageResponse.message.attachments ?? [],
              isGenerating: false,
            };
            return updated;
          });
        } else if ((mode as string) === "database-query") {
          // Handle database query mode - execute and display result inline
          setSqlError(null);
          try {
            const result = await askSqlQuestion(userMessage, activeThreadIdForRequest);
            setSqlResult(result);
            setSqlModalOpen(true);
            
            // If backend created a new thread, notify parent
            if (result.thread_id && result.thread_id !== activeThreadRef.current) {
              onThreadCreated(result.thread_id);
            }
            
            // Reload messages from database to ensure persistence
            const finalThreadId = result.thread_id || activeThreadIdForRequest;
            if (finalThreadId) {
              const refreshed = await getMessages(finalThreadId);
              setMessages(mapMessages(refreshed));
            } else {
              // Fallback: update local state if no thread
              const sqlResponse = `SQL Query: \`\`\`sql\n${result.sql}\n\`\`\`\n\nResult: ${result.answer}`;
              setMessages((prev) => {
                const updated = [...prev];
                const targetIndex = updated.findIndex((message) => message.id === assistantId);
                if (targetIndex !== -1) {
                  updated[targetIndex].content = sqlResponse;
                }
                return updated;
              });
            }
          } catch (err) {
            const message = err instanceof Error ? err.message : "Failed to execute query";
            setSqlError(message);
            setMessages((prev) => {
              const updated = [...prev];
              const targetIndex = updated.findIndex((m) => m.id === assistantId);
              if (targetIndex !== -1) {
                updated[targetIndex] = {
                  ...updated[targetIndex],
                  content: message,
                };
              }
              return updated;
            });
          }
        } else {
          const onToken = (token: string) => {
            setMessages((prev) => {
              if (activeStreamAssistantIdRef.current !== assistantId) {
                return prev;
              }
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last?.id === assistantId) {
                const current = last.content || "";
                if (!token) {
                  return updated;
                }

                // Some streams send cumulative content instead of token deltas.
                // Normalize both patterns to avoid duplicate assistant text.
                if (token.startsWith(current)) {
                  last.content = token;
                } else if (current.endsWith(token) || token === current) {
                  // Ignore duplicate chunk.
                } else {
                  last.content = current + token;
                }
              }
              return updated;
            });
          };

          const returnedThreadId = pdfFiles.length > 0 && activeThreadIdForRequest
            ? await askPdfQuestion(userMessage, onToken, activeThreadIdForRequest)
            : await sendChatMessage(
                userMessage,
                onToken,
                activeThreadIdForRequest ?? undefined,
                uploadedAttachments.map((attachment) => attachment.id),
                (mode as "normal" | "upload" | "upload-pdf" | "generate-image")
              );

          if (returnedThreadId && returnedThreadId !== activeThreadRef.current) {
            onThreadCreated(returnedThreadId);
          }
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Failed to send message";
        setError(msg);
        setMessages((prev) => prev.filter((m) => m.id !== assistantId && m.id !== userMessageId));
      } finally {
        activeStreamAssistantIdRef.current = null;
        setIsLoading(false);
        setIsGeneratingImage(false);
        setIsProcessingPdf(false);
        setUploadProgress(0);
      }
    },
    [threadId, onThreadCreated, uploadMutation, mapMessages]
  );

  return (
    <div className="flex flex-col h-full bg-transparent">
      <div className="flex-1 overflow-y-auto p-5 md:p-6">
        {messages.length === 0 && !isLoading && !error && (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center bg-white/70 border border-slate-200 rounded-2xl px-6 py-8 shadow-sm">
              <p className="text-lg font-semibold text-slate-800 mb-2">Start a conversation</p>
              <p className="text-sm">Ask a question to begin this thread.</p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}

        {error && (
          <div className="mb-6 p-4 bg-rose-50 border border-rose-200 text-rose-700 rounded-xl">
            <p className="font-medium">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        )}



        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSendMessage={handleSendMessage}
        activeThreadId={threadId}
        isLoading={isLoading}
        isGeneratingImage={isGeneratingImage}
        isUploading={uploadMutation.isPending}
        isProcessingPdf={isProcessingPdf}
        uploadProgress={uploadProgress}
        pdfStatus={pdfStatus}
      />

      <SqlResultModal
        result={sqlResult}
        isOpen={sqlModalOpen}
        isLoading={isLoading}
        error={sqlError}
        onClose={() => {
          setSqlModalOpen(false);
          setSqlResult(null);
          setSqlError(null);
        }}
      />
    </div>
  );
}

