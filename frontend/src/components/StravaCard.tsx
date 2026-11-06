import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { disconnectStrava, fetchStravaStatus, startStravaConnect, syncStrava } from "../api/strava";

export default function StravaCard() {
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["strava-status"], queryFn: fetchStravaStatus });

  const connect = useMutation({ mutationFn: startStravaConnect });
  const sync = useMutation({ mutationFn: syncStrava });
  const disconnect = useMutation({
    mutationFn: disconnectStrava,
    onSuccess: () => {
      sync.reset();
      queryClient.invalidateQueries({ queryKey: ["strava-status"] });
    },
  });

  if (status.isLoading) return null;
  if (status.isError) {
    return <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{status.error.message}</p>;
  }

  const connected = status.data?.connected ?? false;
  const error = connect.error ?? sync.error ?? disconnect.error;

  return (
    <div className="space-y-3 rounded-xl bg-white p-4 shadow">
      {connected ? (
        <>
          <div className="flex items-center justify-between">
            <p className="font-medium">
              <span className="mr-2 inline-block h-2 w-2 rounded-full bg-green-500" />
              Strava connected
            </p>
            <button
              onClick={() => {
                if (window.confirm("Disconnect Strava? Your imported runs will be removed from Run Smart.")) {
                  disconnect.mutate();
                }
              }}
              disabled={disconnect.isPending}
              className="text-sm text-red-600 hover:underline disabled:opacity-50"
            >
              {disconnect.isPending ? "Disconnecting..." : "Disconnect"}
            </button>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => sync.mutate()}
              disabled={sync.isPending}
              className="rounded-lg border border-blue-600 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 disabled:opacity-50"
            >
              {sync.isPending ? "Importing runs (can take a minute)..." : "Sync my runs"}
            </button>
            {sync.data && (
              <span className="text-sm text-slate-600">
                Strava returned {sync.data.activities_found} recent activities · {sync.data.runs_saved} runs saved
              </span>
            )}
          </div>
        </>
      ) : (
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-slate-600">Connect Strava to build a plan from your real running data.</p>
          <button
            onClick={() => connect.mutate()}
            disabled={connect.isPending}
            className="shrink-0 rounded-lg bg-orange-500 px-4 py-2 text-sm font-medium text-white hover:bg-orange-600 disabled:opacity-50"
          >
            {connect.isPending ? "Redirecting..." : "Connect Strava"}
          </button>
        </div>
      )}

      {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error.message}</p>}
    </div>
  );
}