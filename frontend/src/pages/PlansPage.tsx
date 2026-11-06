import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "../api/client";

export default function PlansPage() {
  const { data: plans, isLoading, error } = useQuery({
    queryKey: ["plans"],
    queryFn: () => unwrap(api.GET("/plans")),
  });

  if (isLoading) return <p className="text-slate-600">Loading your plans...</p>;
  if (error) return <p className="rounded-lg bg-red-50 p-3 text-red-700">{error.message}</p>;
  if (!plans || plans.length === 0) {
    return <p className="text-slate-600">No plans yet. You'll be able to create one here soon.</p>;
  }

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-bold">My plans</h1>
      {plans.map((plan) => (
        <div key={plan.id} className="rounded-xl bg-white p-4 shadow">
          <p className="font-medium">{plan.goal_race_km} km race</p>
          <p className="text-sm text-slate-600">
            Race day {plan.race_date} · {plan.weeks_until_race} weeks · {plan.training_days_per_week} days/week
          </p>
        </div>
      ))}
    </div>
  );
}