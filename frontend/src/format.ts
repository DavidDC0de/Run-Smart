// Pace is stored by the backend in SECONDS per km (400 = 6:40 /km).
export function formatPace(secPerKm: number): string {
  const total = Math.round(secPerKm);
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")} /km`;
}

// Turns what the user types ("6:40") into seconds per km (400).
// Returns null if the text isn't in m:ss format.
export function parsePace(text: string): number | null {
  const match = text.trim().match(/^(\d{1,2}):([0-5]\d)$/);
  if (!match) return null;
  return Number(match[1]) * 60 + Number(match[2]);
}

// Dates from the API look like "2027-04-10".
export function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// Plans have no start date, so we count back from race day:
// the last week of the plan is the week before the race.
export function currentWeekNumber(raceDate: string, totalWeeks: number): number {
  const msPerWeek = 7 * 24 * 60 * 60 * 1000;
  const race = new Date(`${raceDate}T00:00:00`).getTime();
  const weeksLeft = Math.ceil((race - Date.now()) / msPerWeek);
  return Math.min(totalWeeks, Math.max(1, totalWeeks - weeksLeft + 1));
}

export const SESSION_LABELS: Record<string, string> = {
  easy: "Easy run",
  interval: "Intervals",
  tempo: "Tempo",
  long_run: "Long run",
};

export const PHASE_LABELS: Record<string, string> = {
  base: "Base",
  build: "Build",
  race_specific: "Race-specific",
  taper: "Taper",
};