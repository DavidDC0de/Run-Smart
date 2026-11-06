import { api, errorMessage, unwrap } from "./client";
import type { components } from "./schema";
import { currentWeekNumber } from "../format";

export type ManualPlanRequest = components["schemas"]["GenerateManualPlan"];
export type PlanDetail = components["schemas"]["PlanDetailOut"];
export type Week = components["schemas"]["WeekOut"];

export function generateManualPlan(body: ManualPlanRequest) {
  return unwrap(api.POST("/plans/generate_manual", { body }));
}

// Also works out which week is "current", here and not during rendering.
export async function fetchPlan(planId: number) {
  const plan = await unwrap(
    api.GET("/plans/{plan_id}", { params: { path: { plan_id: planId } } }),
  );
  return { ...plan, currentWeek: currentWeekNumber(plan.race_date, plan.weeks_until_race) };
}

export function fetchExplanation(planId: number, weekNumber: number) {
  return unwrap(
    api.GET("/plans/{plan_id}/weeks/{week_number}/explanation", {
      params: { path: { plan_id: planId, week_number: weekNumber } },
    }),
  );
}

// DELETE returns 204 (no body), so it can't use unwrap().
export async function deletePlan(planId: number): Promise<void> {
  let result;
  try {
    result = await api.DELETE("/plans/{plan_id}", { params: { path: { plan_id: planId } } });
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  if (result.error !== undefined) throw new Error(errorMessage(result.error));
}
