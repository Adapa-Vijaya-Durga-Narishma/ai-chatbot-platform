import { useState } from "react";
import { LoginForm } from "../components/auth/LoginForm";
import { RegisterForm } from "../components/auth/RegisterForm";

export default function AuthPage() {
  const [view, setView] = useState<"login" | "register">("login");

  return view === "login" ? (
    <LoginForm onSwitchToRegister={() => setView("register")} />
  ) : (
    <RegisterForm onSwitchToLogin={() => setView("login")} />
  );
}
