import { api, errorMessage, unwrap } from "./client";

export function fetchStravaStatus() {
  return unwrap(api.GET("/strava/status"));
}

// Asks the backend for the Strava authorization URL, then sends the browser
// there. Strava later sends the user back to the backend, which redirects
// to /strava/callback on this frontend.
export async function startStravaConnect() {
  const { url } = await unwrap(api.GET("/strava/connect"));
  window.location.assign(url);
}

// Imports the user's recent Strava runs. Can take a while on the first run.
export function syncStrava() {
  return unwrap(api.GET("/strava/sync"));
}

// DELETE returns 204 (no body), so it can't use unwrap().
export async function disconnectStrava(): Promise<void> {
  let result;
  try {
    result = await api.DELETE("/strava/disconnect");
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  // `response.ok` always exists. The generated types have no `error` property
  // for this endpoint (it declares no error responses), so read it through a cast.
  if (!result.response.ok) {
    throw new Error(errorMessage((result as { error?: unknown }).error));
  }
}