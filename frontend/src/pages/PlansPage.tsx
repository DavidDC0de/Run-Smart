import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, unwrap } from "../api/client";
import { formatDate } from "../format";

export default function PlansPage() {
  const { data: plans, isLoading, error } = useQuery({
    queryKey: ["plans"],
    queryFn: () => unwrap(api.GET("/plans")),
  });

  if (isLoading) return <p className="text-slate-600">Loading your plans...</p>;
  if (error) return <p className="rounded-lg bg-red-50 p-3 text-red-700">{error.message}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">My plans</h1>
        <Link to="/plans/new" className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
          New plan
        </Link>
      </div>

      {(!plans || plans.length === 0) && (
        <p className="rounded-xl bg-white p-6 text-center text-slate-600 shadow">
          No plans yet. Create your first one to get started.
        </p>
      )}

      {plans?.map((plan) => (
        <Link key={plan.id} to={`/plans/${plan.id}`} className="block rounded-xl bg-white p-4 shadow hover:shadow-md">
          <p className="font-medium">{plan.goal_race_km} km race</p>
          <p className="text-sm text-slate-600">
            Race day {formatDate(plan.race_date)} · {plan.weeks_until_race} weeks · {plan.training_days_per_week} days/week
          </p>
        </Link>
      ))}
    </div>
  );
}