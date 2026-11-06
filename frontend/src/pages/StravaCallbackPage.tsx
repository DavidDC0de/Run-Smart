import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { syncStrava } from "../api/strava";

// The backend redirects here after Strava, with ?status=<result>
const FAILURE_MESSAGES: Record<string, string> = {
  denied: "You didn't give Run Smart access to your Strava account.",
  invalid_state: "That connection link expired or wasn't valid. Please try connecting again.",
  token_exchange_failed: "Strava rejected the connection. Please try again.",
  strava_unavailable: "Couldn't reach Strava. Please try again in a moment.",
};

export default function StravaCallbackPage() {
  const [params] = useSearchParams();
  const status = params.get("status");
  const queryClient = useQueryClient();

  // Import the runs straight after connecting. (A query, not an effect, so
  // React's dev-mode double render doesn't import twice.)
  const sync = useQuery({
    queryKey: ["strava-sync-after-connect"],
    queryFn: async () => {
      const result = await syncStrava();
      await queryClient.invalidateQueries({ queryKey: ["strava-status"] });
      return result;
    },
    enabled: status === "connected",
    retry: false,
    staleTime: Infinity,
  });

  if (status !== "connected") {
    return (
      <div className="space-y-4 rounded-xl bg-white p-6 shadow">
        <h1 className="text-xl font-bold">Couldn't connect Strava</h1>
        <p className="text-slate-600">{FAILURE_MESSAGES[status ?? ""] ?? "Something went wrong connecting to Strava."}</p>
        <Link to="/" className="inline-block rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
          Back to my plans
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-xl bg-white p-6 shadow">
      <h1 className="text-xl font-bold">Strava connected</h1>

      {sync.isLoading && <p className="text-slate-600">Importing your runs... this can take a minute.</p>}

      {sync.isError && (
        <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">
          You're connected, but importing runs failed: {sync.error.message}. You can retry with "Sync my runs" on the
          My plans page.
        </p>
      )}

      {sync.data && (
        <p className="text-slate-600">
          Strava returned {sync.data.activities_found} recent activities, and {sync.data.runs_saved} runs are saved.
        </p>
      )}

      {!sync.isLoading && (
        <div className="flex gap-3">
          <Link to="/plans/new" className="rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
            Create a plan
          </Link>
          <Link to="/" className="rounded-lg border border-slate-300 px-4 py-2 hover:bg-slate-50">
            My plans
          </Link>
        </div>
      )}
    </div>
  );
}