import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { currentWeekNumber, formatDate, formatPace, parsePace } from "./format";

describe("parsePace", () => {
  it("turns m:ss into seconds per km", () => {
    expect(parsePace("6:40")).toBe(400);
    expect(parsePace("5:05")).toBe(305);
    expect(parsePace("10:00")).toBe(600);
  });

  it("ignores surrounding spaces", () => {
    expect(parsePace("  5:30 ")).toBe(330);
  });

  it.each(["", "640", "6:60", "6:5", "abc", "6.40", "-5:30", "5:30:10"])("rejects %j", (text) => {
    expect(parsePace(text)).toBeNull();
  });
});

describe("formatPace", () => {
  it("turns seconds per km into m:ss /km", () => {
    expect(formatPace(400)).toBe("6:40 /km");
    expect(formatPace(305)).toBe("5:05 /km");
  });

  it("rounds fractional seconds", () => {
    expect(formatPace(359.6)).toBe("6:00 /km");
  });

  it("round-trips with parsePace", () => {
    for (const seconds of [150, 299, 330, 400, 720]) {
      const text = formatPace(seconds).replace(" /km", "");
      expect(parsePace(text)).toBe(seconds);
    }
  });
});

describe("formatDate", () => {
  it("formats an ISO date the British way", () => {
    expect(formatDate("2027-04-10")).toBe("10 Apr 2027");
  });
});

describe("currentWeekNumber", () => {
  const DAY = 24 * 60 * 60 * 1000;
  const isoDaysFromNow = (days: number) => new Date(Date.now() + days * DAY).toLocaleDateString("en-CA");

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-11-09T12:00:00"));
  });
  afterEach(() => vi.useRealTimers());

  it("is week 1 on the day a 20-week plan is created", () => {
    expect(currentWeekNumber(isoDaysFromNow(20 * 7 + 3), 20)).toBe(1);
  });

  it("moves forward one week at a time", () => {
    expect(currentWeekNumber(isoDaysFromNow(13 * 7), 20)).toBe(8);
    expect(currentWeekNumber(isoDaysFromNow(10 * 7), 20)).toBe(11);
  });

  it("is the final week when race day is days away", () => {
    expect(currentWeekNumber(isoDaysFromNow(1), 20)).toBe(20);
    expect(currentWeekNumber(isoDaysFromNow(6), 20)).toBe(20);
  });

  it("never goes past the last week once the race has happened", () => {
    expect(currentWeekNumber(isoDaysFromNow(-10), 20)).toBe(20);
  });

  it("never goes below week 1", () => {
    expect(currentWeekNumber(isoDaysFromNow(60 * 7), 20)).toBe(1);
  });
});
