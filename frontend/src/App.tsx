import { Link, Navigate, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import LoginPage from "./pages/LoginPage";
import NewPlanPage from "./pages/NewPlanPage";
import PlanDetailPage from "./pages/PlanDetailPage";
import PlansPage from "./pages/PlansPage";
import StravaCallbackPage from "./pages/StravaCallbackPage";

function ProtectedLayout() {
  const { isLoggedIn, signOut } = useAuth();
  if (!isLoggedIn) return <Navigate to="/login" replace />;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between p-4">
          <Link to="/" className="text-lg font-bold">
            Run Smart
          </Link>
          <button onClick={signOut} className="text-sm text-slate-600 hover:text-slate-900">
            Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl p-4">
        <Outlet />
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/strava/callback" element={<StravaCallbackPage />} />
        <Route path="/" element={<PlansPage />} />
        <Route path="/plans/new" element={<NewPlanPage />} />
        <Route path="/plans/:planId" element={<PlanDetailPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}