import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AttachmentList } from "../attachments/AttachmentList";
import type { ChatMessage as IChatMessage } from "../../types/chat";

interface ChatMessageProps {
  message: IChatMessage;
}

export function ChatMessage({ message }: ChatMessageProps) {
  // Memoize markdown rendering to avoid re-renders on every parent update
  const renderedContent = useMemo(
    () => (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: ({ children }) => (
            <div className="overflow-x-auto">
              <table className="min-w-full border-collapse">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="border border-slate-300 px-2 py-1 text-left">{children}</th>,
          td: ({ children }) => <td className="border border-slate-200 px-2 py-1 align-top">{children}</td>,
        }}
      >
        {message.content}
      </ReactMarkdown>
    ),
    [message.content]
  );

  const isUser = message.role === "user";
  const isGenerating = Boolean(message.isGenerating);

  return (
    <div
      className={`flex gap-4 mb-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {/* Message bubble with text-justify for proper alignment */}
      <div
        className={`max-w-2xl px-4 py-3 rounded-2xl border text-justify shadow-sm ${
          isUser
            ? "bg-sky-700 border-sky-700 text-white rounded-br-md"
            : "bg-white border-slate-200 text-slate-800 rounded-bl-md"
        }`}
      >
        <AttachmentList attachments={message.attachments} />
        {isGenerating ? (
          <div className={`text-sm ${isUser ? "text-sky-100" : "text-slate-600"}`}>
            <span className="animate-pulse">Generating image...</span>
          </div>
        ) : (
          <div className={`prose prose-sm max-w-none ${isUser ? "prose-invert" : ""}`}>
            {renderedContent}
          </div>
        )}
        <div
          className={`text-xs mt-2 ${
            isUser ? "text-sky-100" : "text-slate-400"
          }`}
        >
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
