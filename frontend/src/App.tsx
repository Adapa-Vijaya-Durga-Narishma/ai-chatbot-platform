import { AuthProvider, useAuth } from "./context/AuthContext";
import { Navigate, Route, Routes } from "react-router-dom";
import AuthPage from "./pages/AuthPage";
import ChatPage from "./pages/ChatPage";
import DataframeChatPage from "./pages/DataframeChatPage";
import ResearchDigestPage from "./pages/ResearchDigestPage";
import SqlChatPage from "./pages/SqlChatPage";
import TicTacToePage from "./pages/TicTacToePage";

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-gray-500 dark:text-gray-400">Loading…</div>
      </div>
    );
  }

  if (!user) {
    return <AuthPage />;
  }

  return (
    <Routes>
      <Route path="/" element={<ChatPage />} />
      <Route path="/dataframe" element={<DataframeChatPage />} />
      <Route path="/sql" element={<SqlChatPage />} />
      <Route path="/research" element={<ResearchDigestPage />} />
      <Route path="/tic-tac-toe" element={<TicTacToePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

