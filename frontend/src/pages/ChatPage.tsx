import { useEffect, useMemo, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import {
  createThread,
  deleteThread,
  getThreads,
  renameThread,
} from "../lib/api";
import { ChatWindow } from "../components/chat/ChatWindow";
import { ThreadSidebar } from "../components/chat/ThreadSidebar";
import type { ChatThread } from "../types/chat";

export default function ChatPage() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null);

  const threadsQuery = useQuery({
    queryKey: ["threads", user?.id],
    queryFn: getThreads,
    enabled: Boolean(user?.id),
  });

  const threads = useMemo<ChatThread[]>(() => threadsQuery.data ?? [], [threadsQuery.data]);

  useEffect(() => {
    if (!activeThreadId) return;
    const stillExists = threads.some((t) => t.id === activeThreadId);
    if (!stillExists) {
      setActiveThreadId(null);
    }
  }, [threads, activeThreadId]);

  const createThreadMutation = useMutation({
    mutationFn: () => createThread(),
    onSuccess: (thread) => {
      queryClient.setQueryData<ChatThread[]>(["threads", user?.id], (old = []) => [thread, ...old]);
      setActiveThreadId(thread.id);
    },
  });

  const renameThreadMutation = useMutation({
    mutationFn: ({ id, title }: { id: string; title: string }) => renameThread(id, title),
    onSuccess: (updated) => {
      queryClient.setQueryData<ChatThread[]>(["threads", user?.id], (old = []) =>
        old.map((thread) => (thread.id === updated.id ? updated : thread))
      );
    },
  });

  const deleteThreadMutation = useMutation({
    mutationFn: (id: string) => deleteThread(id),
    onSuccess: (_data, deletedId) => {
      queryClient.setQueryData<ChatThread[]>(["threads", user?.id], (old = []) =>
        old.filter((thread) => thread.id !== deletedId)
      );
      if (activeThreadId === deletedId) {
        setActiveThreadId(null);
      }
    },
  });

  function handleSelectThread(id: string) {
    setActiveThreadId(id);
  }

  function handleThreadCreated(id: string) {
    setActiveThreadId(id);
    queryClient.invalidateQueries({ queryKey: ["threads", user?.id] });
  }

  return (
    <div className="h-screen flex flex-col p-3 md:p-5 gap-3 md:gap-4">
      <header className="flex items-center justify-between px-4 md:px-5 py-3 rounded-2xl border border-slate-200/80 bg-white/85 backdrop-blur shadow-sm flex-shrink-0">
        <div>
          <h1 className="text-base md:text-lg font-semibold text-slate-900">Amzur AI Chat</h1>
          <p className="text-xs text-slate-500">{user?.email}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/tic-tac-toe"
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Tic Tac Toe
          </Link>
          <Link
            to="/research"
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Research Digest
          </Link>
          <Link
            to="/dataframe"
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Dataframe Chat
          </Link>
          <button
            onClick={logout}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-100 transition-colors"
          >
            Sign out
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden rounded-2xl border border-slate-200/80 bg-white/80 backdrop-blur shadow-sm">
        <ThreadSidebar
          threads={threads}
          activeThreadId={activeThreadId}
          onSelectThread={handleSelectThread}
          onNewChat={() => createThreadMutation.mutate()}
          onRenameThread={(id, title) => renameThreadMutation.mutate({ id, title })}
          onDeleteThread={(id) => deleteThreadMutation.mutate(id)}
        />

        <main className="flex-1 flex flex-col overflow-hidden bg-slate-50/80">
          <ChatWindow threadId={activeThreadId} onThreadCreated={handleThreadCreated} />
        </main>
      </div>
    </div>
  );
}
