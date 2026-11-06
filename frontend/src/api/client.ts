import createClient, { type Middleware } from "openapi-fetch";
import type { paths } from "./schema";

const TOKEN_KEY = "runsmart_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

// Attaches the token to every request, and logs the user out if the
// backend says the token is no longer valid (expired, user deleted, etc).
const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = getToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401 && getToken()) {
      clearToken();
      window.location.assign("/login");
    }
    return response;
  },
};

export const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL });
api.use(authMiddleware);

// The backend returns errors in two shapes:
//   { detail: "some string" }                      (login 403, 404, 400, ...)
//   { detail: [{ loc: [...], msg: "..." }, ...] }  (422 validation errors)
export function errorMessage(error: unknown): string {
  const detail = (error as { detail?: unknown } | undefined)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = d.loc?.filter((part) => part !== "body").join(".");
        return field ? `${field}: ${d.msg}` : (d.msg ?? "Invalid value");
      })
      .join("; ");
  }
  return "Something went wrong. Please try again.";
}

// Turns an API call into a promise that returns the data, or throws an
// Error with a message that is safe to show to the user.
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  let result;
  try {
    result = await call;
  } catch {
    throw new Error("Can't reach the server. Is the backend running?");
  }
  if (result.error !== undefined || result.data === undefined) {
    throw new Error(errorMessage(result.error));
  }
  return result.data;
}