import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deletePlan, fetchExplanation, fetchPlan, type Week } from "../api/plans";
import { PHASE_LABELS, SESSION_LABELS, formatDate, formatPace } from "../format";

function WeekCard({
  planId,
  week,
  isOpen,
  isCurrent,
  onToggle,
}: {
  planId: number;
  week: Week;
  isOpen: boolean;
  isCurrent: boolean;
  onToggle: () => void;
}) {
  // The current week explains itself automatically; other weeks wait for a click
  // so we don't spend OpenAI credit on weeks nobody reads.
  const [wantExplanation, setWantExplanation] = useState(isCurrent);

  const explanation = useQuery({
    queryKey: ["explanation", planId, week.week_number],
    queryFn: () => fetchExplanation(planId, week.week_number),
    enabled: isOpen && wantExplanation,
    staleTime: Infinity,
    retry: false,
  });

  return (
    <div className={`rounded-xl bg-white shadow ${isCurrent ? "ring-2 ring-blue-500" : ""}`}>
      <button
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div>
          <span className="font-medium">Week {week.week_number}</span>
          <span className="ml-2 text-sm text-slate-600">
            {PHASE_LABELS[week.phase] ?? week.phase} · {week.total_km} km
          </span>
          {isCurrent && (
            <span className="ml-2 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">This week</span>
          )}
        </div>
        <span className="text-slate-400">{isOpen ? "−" : "+"}</span>
      </button>

      {isOpen && (
        <div className="space-y-4 border-t border-slate-100 p-4">
          <ul className="space-y-2">
            {week.sessions.map((s, i) => (
              <li key={i} className="flex items-center justify-between rounded-lg bg-slate-50 p-3 text-sm">
                <span>
                  <span className="font-medium">{s.day}</span> · {SESSION_LABELS[s.type] ?? s.type}
                </span>
                <span className="text-slate-600">
                  {s.distance_km.toFixed(1)} km @ {formatPace(s.pace_sec_per_km)}
                </span>
              </li>
            ))}
          </ul>

          <div>
            {!wantExplanation && (
              <button
                onClick={() => setWantExplanation(true)}
                className="rounded-lg border border-blue-600 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50"
              >
                Explain this week
              </button>
            )}
            {wantExplanation && explanation.isLoading && (
              <p className="text-sm text-slate-500">Writing your explanation...</p>
            )}
            {wantExplanation && explanation.isError && (
              <div className="space-y-2">
                <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{explanation.error.message}</p>
                <button
                  onClick={() => explanation.refetch()}
                  className="rounded-lg border border-slate-300 px-3 py-1 text-sm"
                >
                  Try again
                </button>
              </div>
            )}
            {explanation.data && (
              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700">
                {explanation.data.explanation}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function PlanDetailPage() {
  const { planId } = useParams();
  const id = Number(planId);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // undefined = the user hasn't picked a week yet, so show the current one
  const [openWeek, setOpenWeek] = useState<number | null | undefined>(undefined);

  const { data: plan, isLoading, error } = useQuery({
    queryKey: ["plan", id],
    queryFn: () => fetchPlan(id),
    enabled: Number.isFinite(id),
  });

  const remove = useMutation({
    mutationFn: () => deletePlan(id),
    onSuccess: () => {
      queryClient.removeQueries({ queryKey: ["plan", id] });
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      navigate("/");
    },
  });

  if (!Number.isFinite(id)) return <p className="text-slate-600">That plan doesn't exist.</p>;
  if (isLoading) return <p className="text-slate-600">Loading your plan...</p>;
  if (error) {
    return (
      <div className="space-y-3">
        <p className="rounded-lg bg-red-50 p-3 text-red-700">{error.message}</p>
        <Link to="/" className="text-blue-600 hover:underline">
          Back to my plans
        </Link>
      </div>
    );
  }
  if (!plan) return null;

  const activeWeek = openWeek === undefined ? plan.currentWeek : openWeek;

  return (
    <div className="space-y-4">
      <Link to="/" className="text-sm text-slate-600 hover:underline">
        ← My plans
      </Link>

      <div className="rounded-xl bg-white p-4 shadow">
        <h1 className="text-xl font-bold">{plan.goal_race_km} km plan</h1>
        <p className="text-sm text-slate-600">
          Race day {formatDate(plan.race_date)} · {plan.weeks_until_race} weeks · {plan.training_days_per_week}{" "}
          days/week
        </p>
      </div>

      <div className="space-y-3">
        {plan.weeks.map((week) => (
          <WeekCard
            key={week.week_number}
            planId={plan.id}
            week={week}
            isOpen={activeWeek === week.week_number}
            isCurrent={plan.currentWeek === week.week_number}
            onToggle={() => setOpenWeek(activeWeek === week.week_number ? null : week.week_number)}
          />
        ))}
      </div>

      {remove.isError && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{remove.error.message}</p>}
      <button
        onClick={() => {
          if (window.confirm("Delete this plan? This can't be undone.")) remove.mutate();
        }}
        disabled={remove.isPending}
        className="text-sm text-red-600 hover:underline disabled:opacity-50"
      >
        {remove.isPending ? "Deleting..." : "Delete this plan"}
      </button>
    </div>
  );
}