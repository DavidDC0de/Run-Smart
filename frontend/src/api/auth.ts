import { api, unwrap } from "./client";

// The backend's login endpoint takes a FORM (not JSON), and the field
// holding the email is called "username".
export function login(email: string, password: string) {
  return unwrap(
    api.POST("/user/login", {
      body: { username: email, password, scope: "" },
      bodySerializer: (body) =>
        new URLSearchParams({ username: body.username, password: body.password }).toString(),
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  );
}

export function signup(email: string, password: string) {
  return unwrap(api.POST("/user/signup", { body: { email, password } }));
}