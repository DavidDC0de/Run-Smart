import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { generateManualPlan } from "../api/plans";
import { parsePace } from "../format";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const DISTANCES = [5, 10, 21, 42] as const;
type Distance = (typeof DISTANCES)[number];
const DISTANCE_LABELS: Record<Distance, string> = {
  5: "5K",
  10: "10K",
  21: "Half marathon",
  42: "Marathon",
};

// The backend only accepts races 6 to 52 weeks away.
function daysFromNow(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toLocaleDateString("en-CA"); // YYYY-MM-DD in local time
}
const MIN_DATE = daysFromNow(43);
const MAX_DATE = daysFromNow(363);

const inputClass = "w-full rounded-lg border border-slate-300 p-2";

export default function NewPlanPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [distance, setDistance] = useState<Distance>(10);
  const [raceDate, setRaceDate] = useState("");
  const [goalMinutes, setGoalMinutes] = useState("");
  const [trainingDays, setTrainingDays] = useState(4);
  const [days, setDays] = useState<string[]>([]);
  const [avgWeeklyKm, setAvgWeeklyKm] = useState("");
  const [longestRunKm, setLongestRunKm] = useState("");
  const [weeksTrained, setWeeksTrained] = useState("4");
  const [longestRunPace, setLongestRunPace] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: generateManualPlan,
    onSuccess: (plan) => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      navigate(`/plans/${plan.id}`);
    },
  });

  function toggleDay(day: string) {
    setDays((current) => (current.includes(day) ? current.filter((d) => d !== day) : [...current, day]));
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);

    const pace = parsePace(longestRunPace);
    if (pace === null) {
      setFormError("Enter your long-run pace as minutes:seconds per km, e.g. 6:40");
      return;
    }
    if (days.length < trainingDays) {
      setFormError(`Pick at least ${trainingDays} available days (you chose ${days.length}).`);
      return;
    }

    mutation.mutate({
      goal_race_km: distance,
      race_date: raceDate,
      goal_time_min: Number(goalMinutes),
      training_days_per_week: trainingDays,
      available_days: days,
      average_weekly_km: Number(avgWeeklyKm),
      longest_run_km: Number(longestRunKm),
      weeks_trained_last_8: Number(weeksTrained),
      longest_run_pace: pace,
    });
  }

  const shownError = formError ?? (mutation.isError ? mutation.error.message : null);

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-xl bg-white p-5 shadow">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">New training plan</h1>
        <Link to="/" className="text-sm text-slate-600 hover:underline">
          Cancel
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block space-y-1">
          <span className="text-sm font-medium">Race distance</span>
          <select
            value={distance}
            onChange={(e) => setDistance(Number(e.target.value) as Distance)}
            className={inputClass}
          >
            {DISTANCES.map((d) => (
              <option key={d} value={d}>
                {DISTANCE_LABELS[d]}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">Race date</span>
          <input
            type="date"
            required
            min={MIN_DATE}
            max={MAX_DATE}
            value={raceDate}
            onChange={(e) => setRaceDate(e.target.value)}
            className={inputClass}
          />
          <span className="text-xs text-slate-500">Between 6 and 52 weeks from today.</span>
        </label>

        <label className="block space-y-1 sm:col-span-2">
          <span className="text-sm font-medium">Goal finish time (minutes)</span>
          <input
            type="number"
            required
            min={1}
            step="any"
            placeholder="e.g. 55 for a 55-minute 10K"
            value={goalMinutes}
            onChange={(e) => setGoalMinutes(e.target.value)}
            className={inputClass}
          />
        </label>
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium">Training days per week</span>
        <div className="flex gap-2">
          {[3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setTrainingDays(n)}
              className={`rounded-lg border px-4 py-2 ${
                trainingDays === n ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 bg-white"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <span className="text-sm font-medium">Days you can run (pick at least {trainingDays})</span>
        <div className="flex flex-wrap gap-2">
          {DAYS.map((day) => (
            <button
              key={day}
              type="button"
              onClick={() => toggleDay(day)}
              className={`rounded-lg border px-3 py-2 text-sm ${
                days.includes(day) ? "border-blue-600 bg-blue-600 text-white" : "border-slate-300 bg-white"
              }`}
            >
              {day.slice(0, 3)}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">The long run goes on the last day you pick in the week.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block space-y-1">
          <span className="text-sm font-medium">Average weekly distance (km)</span>
          <input
            type="number"
            required
            min={0}
            max={300}
            step="any"
            value={avgWeeklyKm}
            onChange={(e) => setAvgWeeklyKm(e.target.value)}
            className={inputClass}
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">Longest recent run (km)</span>
          <input
            type="number"
            required
            min={0}
            max={100}
            step="any"
            value={longestRunKm}
            onChange={(e) => setLongestRunKm(e.target.value)}
            className={inputClass}
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">Weeks you trained in the last 8</span>
          <select value={weeksTrained} onChange={(e) => setWeeksTrained(e.target.value)} className={inputClass}>
            {[0, 1, 2, 3, 4, 5, 6, 7, 8].map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>

        <label className="block space-y-1">
          <span className="text-sm font-medium">Pace of that long run (min:sec per km)</span>
          <input
            type="text"
            required
            inputMode="numeric"
            placeholder="6:40"
            value={longestRunPace}
            onChange={(e) => setLongestRunPace(e.target.value)}
            className={inputClass}
          />
        </label>
      </div>

      {shownError && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{shownError}</p>}

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full rounded-lg bg-blue-600 p-3 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {mutation.isPending ? "Building your plan..." : "Generate plan"}
      </button>
    </form>
  );
}