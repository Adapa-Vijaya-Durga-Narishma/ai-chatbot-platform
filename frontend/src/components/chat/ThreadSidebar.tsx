import { useState } from "react";

import type { ChatThread } from "../../types/chat";

interface Props {
  threads: ChatThread[];
  activeThreadId: string | null;
  onSelectThread: (id: string) => void;
  onNewChat: () => void;
  onRenameThread: (id: string, title: string) => void;
  onDeleteThread: (id: string) => void;
}

export function ThreadSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onNewChat,
  onRenameThread,
  onDeleteThread,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");

  function startEdit(thread: ChatThread) {
    setEditingId(thread.id);
    setEditingTitle(thread.title ?? "");
  }

  function submitEdit(id: string) {
    const trimmed = editingTitle.trim();
    if (trimmed) {
      onRenameThread(id, trimmed);
    }
    setEditingId(null);
    setEditingTitle("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditingTitle("");
  }

  return (
    <aside className="w-72 flex-shrink-0 border-r border-slate-200 bg-white/70 flex flex-col h-full">
      <div className="p-3 border-b border-slate-200">
        <button
          onClick={onNewChat}
          className="w-full py-2 px-3 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition-colors"
        >
          + New Chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto p-2 space-y-2">
        {threads.length === 0 && (
          <p className="text-slate-500 text-sm px-2 py-4 text-center">No chats yet</p>
        )}

        {threads.map((t) => {
          const isActive = t.id === activeThreadId;
          const isEditing = t.id === editingId;

          return (
            <div
              key={t.id}
              className={`rounded-xl border transition-colors ${
                isActive
                  ? "border-slate-300 bg-white shadow-sm"
                  : "border-slate-200 bg-slate-50/60"
              }`}
            >
              {isEditing ? (
                <div className="p-2 space-y-2">
                  <input
                    value={editingTitle}
                    onChange={(e) => setEditingTitle(e.target.value)}
                    className="w-full px-2 py-1 rounded-lg bg-white text-slate-700 text-sm border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-300"
                    autoFocus
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => submitEdit(t.id)}
                      className="px-2 py-1 text-xs rounded-lg bg-slate-900 text-white hover:bg-slate-800"
                    >
                      Save
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="px-2 py-1 text-xs rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-2 flex items-center gap-2">
                  <button
                    onClick={() => onSelectThread(t.id)}
                    className={`flex-1 min-w-0 text-left px-2 py-1 rounded text-sm truncate transition-colors ${
                      isActive
                        ? "text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    {t.title ?? "Untitled Chat"}
                  </button>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <button
                      onClick={() => startEdit(t)}
                      aria-label="Rename thread"
                      title="Rename"
                      className="h-7 w-7 inline-flex items-center justify-center rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="h-3.5 w-3.5"
                      >
                        <path d="M12 20h9" />
                        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => onDeleteThread(t.id)}
                      aria-label="Delete thread"
                      title="Delete"
                      className="h-7 w-7 inline-flex items-center justify-center rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        className="h-3.5 w-3.5"
                      >
                        <path d="M3 6h18" />
                        <path d="M8 6V4h8v2" />
                        <path d="M19 6l-1 14H6L5 6" />
                        <path d="M10 11v6" />
                        <path d="M14 11v6" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
