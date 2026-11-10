import { describe, expect, it } from "vitest";
import { errorMessage, unwrap } from "./client";

describe("errorMessage", () => {
  it("passes through the plain-string errors (login 403, 404, 400...)", () => {
    expect(errorMessage({ detail: "Invalid Credentials!" })).toBe("Invalid Credentials!");
  });

  it("turns 422 validation lists into 'field: message'", () => {
    const error = {
      detail: [
        { loc: ["body", "race_date"], msg: "Race must be at least 6 weeks away.", type: "value_error" },
        { loc: ["body", "goal_time_min"], msg: "Field required", type: "missing" },
      ],
    };
    expect(errorMessage(error)).toBe(
      "race_date: Race must be at least 6 weeks away.; goal_time_min: Field required",
    );
  });

  it("copes with a validation error that has no location", () => {
    expect(errorMessage({ detail: [{ msg: "Something is off" }] })).toBe("Something is off");
  });

  it.each([undefined, null, {}, { detail: 42 }, "nope"])("falls back to a friendly message for %j", (error) => {
    expect(errorMessage(error)).toBe("Something went wrong. Please try again.");
  });
});

describe("unwrap", () => {
  it("returns the data on success", async () => {
    await expect(unwrap(Promise.resolve({ data: { id: 1 } }))).resolves.toEqual({ id: 1 });
  });

  it("throws the backend's message on an API error", async () => {
    await expect(unwrap(Promise.resolve({ error: { detail: "Plan not found" } }))).rejects.toThrow("Plan not found");
  });

  it("throws when there is neither data nor an error", async () => {
    await expect(unwrap(Promise.resolve({}))).rejects.toThrow("Something went wrong");
  });

  it("explains when the backend can't be reached", async () => {
    await expect(unwrap(Promise.reject(new TypeError("fetch failed")))).rejects.toThrow("Can't reach the server");
  });
});
