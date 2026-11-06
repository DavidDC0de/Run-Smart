import { useState, type FormEvent } from "react";
import { Navigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { login, signup } from "../api/auth";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { isLoggedIn, signIn } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: async () => {
      if (mode === "signup") await signup(email, password);
      return login(email, password);
    },
    onSuccess: (data) => signIn(data.access_token),
  });

  if (isLoggedIn) return <Navigate to="/" replace />;

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4 rounded-xl bg-white p-6 shadow">
        <h1 className="text-2xl font-bold">Run Smart</h1>
        <p className="text-sm text-slate-600">
          {mode === "login" ? "Log in to see your training plans." : "Create an account to get started."}
        </p>

        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-slate-300 p-2"
        />
        <input
          type="password"
          required
          minLength={mode === "signup" ? 8 : undefined}
          maxLength={72}
          placeholder={mode === "signup" ? "Password (8+ characters)" : "Password"}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-300 p-2"
        />

        {mutation.isError && (
          <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{mutation.error.message}</p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full rounded-lg bg-blue-600 p-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? "Please wait..." : mode === "login" ? "Log in" : "Sign up"}
        </button>

        <button
          type="button"
          onClick={() => {
            mutation.reset();
            setMode(mode === "login" ? "signup" : "login");
          }}
          className="w-full text-sm text-blue-600 hover:underline"
        >
          {mode === "login" ? "No account? Sign up" : "Have an account? Log in"}
        </button>
      </form>
    </div>
  );
}