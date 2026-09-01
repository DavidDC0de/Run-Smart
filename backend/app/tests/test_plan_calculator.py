"""
Tests for the PURE functions in plan.py — no database, no mocking.
These test calculation logic in isolation, feeding known inputs and
checking the output makes sense.

Functions needing the DB (calculate_fitness_summary, generate_training_plan)
are NOT covered here — those come once we have your model files.
"""

from app.services.plan import (  # adjust import path to match your project
    calculate_fitness_score,
    determine_phases,
    determine_week_phase,
    is_recovery_week,
    calculate_starting_volume,
    calculate_training_paces,
    calculate_weekly_volume,
    choose_quality_session,
    calculate_long_run,
    progress_training_pace,
    generate_week_sessions,
)


# ---------------------------------------------------------------------------
# calculate_fitness_score
# ---------------------------------------------------------------------------

def test_fitness_score_low_volume_low_consistency():
    """
    A beginner-ish runner: low weekly km, poor consistency, short longest run.
    Score should land in the lower range (roughly 20s-30s), never below 1.
    """
    score = calculate_fitness_score(
        avg_weekly_km=10,
        longest_run_km=5,
        training_consistency=1,
        zone_2_percentage=50,
    )
    assert 1 <= score <= 100
    assert score < 40  # low inputs should not produce a high score


def test_fitness_score_high_volume_high_consistency():
    """
    A well-trained runner: high weekly km, full consistency, long runs done.
    Score should land high, close to the top of the range.
    """
    score = calculate_fitness_score(
        avg_weekly_km=70,
        longest_run_km=28,
        training_consistency=8,
        zone_2_percentage=70,
    )
    assert score > 80


def test_fitness_score_never_exceeds_bounds():
    """
    Even with extreme/unrealistic inputs, score must stay clamped 1-100
    (the function does `max(1, min(100, score))`).
    """
    score = calculate_fitness_score(
        avg_weekly_km=500,
        longest_run_km=100,
        training_consistency=8,
        zone_2_percentage=100,
    )
    assert score <= 100


def test_fitness_score_zone_2_branch_currently_never_runs():
    """
    KNOWN ISSUE: `if zone_2_percentage is not int` checks whether the value
    IS the type `int` itself, not whether it's a number — this is always
    True for any real number you pass in, so the zone-2 adjustment branch
    is unreachable and zone_2_adjustment is always 0.

    This test documents CURRENT behavior: passing a low vs high zone_2_percentage
    makes NO difference to the score right now. If you fix the `isinstance` check,
    this test should start failing — that's your signal the fix worked, and you'd
    update this test to assert the scores DO differ.
    """
    score_low_zone2 = calculate_fitness_score(
        avg_weekly_km=40, longest_run_km=15, training_consistency=5, zone_2_percentage=20
    )
    score_high_zone2 = calculate_fitness_score(
        avg_weekly_km=40, longest_run_km=15, training_consistency=5, zone_2_percentage=90
    )
    assert score_low_zone2 == score_high_zone2  # currently true due to the bug


# ---------------------------------------------------------------------------
# determine_phases
# ---------------------------------------------------------------------------

def test_determine_phases_sums_to_total_weeks():
    """
    The four phases (base + build + race_specific + taper) should always
    add up to the total number of weeks you gave it — no weeks should
    get lost or double-counted.
    """
    total_weeks = 16
    phases = determine_phases(total_weeks)
    assert phases["base"] + phases["build"] + phases["race_specific"] + phases["taper"] == total_weeks


def test_determine_phases_taper_always_two_weeks():
    phases = determine_phases(20)
    assert phases["taper"] == 2


def test_determine_phases_short_plan_still_has_minimum_phases():
    """
    Even a short training block (e.g. 6 weeks) should still get at least
    2 weeks of base and 2 weeks of build per the `max(2, ...)` floors.
    """
    phases = determine_phases(6)
    assert phases["base"] >= 2
    assert phases["build"] >= 2


# ---------------------------------------------------------------------------
# determine_week_phase
# ---------------------------------------------------------------------------

def test_determine_week_phase_returns_correct_phase_for_each_stage():
    phases = {"base": 4, "build": 6, "race_specific": 4, "taper": 2}
    # base: weeks 1-4, build: weeks 5-10, race_specific: weeks 11-14, taper: weeks 15-16
    assert determine_week_phase(1, phases) == "base"
    assert determine_week_phase(4, phases) == "base"
    assert determine_week_phase(5, phases) == "build"
    assert determine_week_phase(10, phases) == "build"
    assert determine_week_phase(11, phases) == "race_specific"
    assert determine_week_phase(15, phases) == "taper"
    assert determine_week_phase(16, phases) == "taper"


# ---------------------------------------------------------------------------
# is_recovery_week
# ---------------------------------------------------------------------------

def test_is_recovery_week_every_fourth_week():
    assert is_recovery_week(4, "base") is True
    assert is_recovery_week(8, "build") is True
    assert is_recovery_week(3, "base") is False


def test_is_recovery_week_never_true_during_taper():
    """Taper weeks are never treated as recovery weeks, even on week 4/8/etc multiples."""
    assert is_recovery_week(8, "taper") is False


# ---------------------------------------------------------------------------
# calculate_starting_volume
# ---------------------------------------------------------------------------

def test_starting_volume_uses_average_for_consistent_runner():
    summary = {"average_weekly_km": 30, "training_consistancy": 6, "longest_recent_run_km": 12}
    assert calculate_starting_volume(summary) == 30


def test_starting_volume_caps_detrained_runner():
    """
    A runner with low consistency (<=2 active weeks recently) is treated as
    'detrained' — starting volume is capped at whichever is smallest of
    (2x average, 2x longest run, 20km), so the plan doesn't start too aggressively.
    """
    summary = {"average_weekly_km": 50, "training_consistancy": 1, "longest_recent_run_km": 5}
    result = calculate_starting_volume(summary)
    assert result == min(50 * 2, 5 * 2, 20)
    assert result == 10  # smallest of the three (5*2)


# ---------------------------------------------------------------------------
# calculate_training_paces
# ---------------------------------------------------------------------------

def test_training_paces_easy_slower_than_current():
    """Easy pace should always be slower (higher seconds/km) than current fitness pace."""
    paces = calculate_training_paces(goal_pace=300, average_pace=330, current_pace=320)
    assert paces["easy"] > 320


def test_training_paces_race_pace_equals_goal():
    paces = calculate_training_paces(goal_pace=300, average_pace=330, current_pace=320)
    assert paces["race"] == 300


def test_training_paces_current_pace_capped_by_average_plus_60():
    """
    `current_pace = min(current_pace, average_pace + 60)` — if someone's current_pace
    input is faster than average+60 allows, it gets capped. Verify the cap applies.
    """
    paces = calculate_training_paces(goal_pace=300, average_pace=330, current_pace=100)
    # current_pace effectively becomes min(100, 390) = 100, so pace_gap = current - goal
    # this test just confirms no crash and easy > current used internally
    assert paces["easy"] == 160  # 100 + 60


# ---------------------------------------------------------------------------
# calculate_weekly_volume
# ---------------------------------------------------------------------------

def test_weekly_volume_week_one_returns_starting_volume():
    result = calculate_weekly_volume(starting_volume=20, week_number=1, previous_volume=0, phase="base")
    assert result == 20


def test_weekly_volume_recovery_week_reduces_by_20_percent():
    result = calculate_weekly_volume(starting_volume=20, week_number=4, previous_volume=40, phase="base")
    assert result == 40 * 0.80


def test_weekly_volume_taper_reduces_by_30_percent():
    result = calculate_weekly_volume(starting_volume=20, week_number=15, previous_volume=40, phase="taper")
    assert result == 40 * 0.70


def test_weekly_volume_build_phase_increases_by_8_percent():
    result = calculate_weekly_volume(starting_volume=20, week_number=5, previous_volume=40, phase="build")
    assert result == 40 * 1.08


# ---------------------------------------------------------------------------
# choose_quality_session
# ---------------------------------------------------------------------------

def test_choose_quality_session_alternates():
    assert choose_quality_session(2) == "tempo"
    assert choose_quality_session(3) == "interval"


# ---------------------------------------------------------------------------
# calculate_long_run
# ---------------------------------------------------------------------------

def test_long_run_increases_by_8_percent_normally():
    result = calculate_long_run(previous_long_run=10, week_number=5, race_distance=42, phase="build")
    assert result == min(10 * 1.08, 42 * 0.9)


def test_long_run_reduces_during_taper():
    result = calculate_long_run(previous_long_run=20, week_number=15, race_distance=42, phase="taper")
    assert result == 20 * 0.70


def test_long_run_capped_at_90_percent_of_race_distance():
    """Long run should never exceed 90% of race distance, even after repeated increases."""
    result = calculate_long_run(previous_long_run=40, week_number=10, race_distance=42, phase="build")
    assert result == 42 * 0.9


def test_long_run_phase_recovery_branch_is_unreachable():
    """
    KNOWN ISSUE: this function checks `if phase == "recovery"`, but
    determine_week_phase() never actually returns "recovery" as a phase name
    (recovery weeks are identified separately, by week number, and keep
    whatever phase they're in — e.g. still "base" or "build").
    So this branch can never trigger. This test documents that a recovery
    WEEK (e.g. week 4, which reduces weekly volume) does NOT reduce the
    long run distance, since phase is still "base"/"build", not "recovery".
    """
    result = calculate_long_run(previous_long_run=10, week_number=4, race_distance=42, phase="base")
    assert result == min(10 * 1.08, 42 * 0.9)  # normal increase, no reduction applied


# ---------------------------------------------------------------------------
# progress_training_pace
# ---------------------------------------------------------------------------

def test_progress_training_pace_no_progression_in_week_zero_ratio():
    """At week_number=0 out of total_weeks, progress fraction is 0, so no improvement yet."""
    result = progress_training_pace(
        base_pace=300, current_pace=330, goal_pace=280,
        week_number=0, total_weeks=16, workout_type="easy", phase="base"
    )
    assert result == 300  # no improvement applied


def test_progress_training_pace_taper_has_zero_multiplier():
    """Taper phase has phase_multiplier 0.0, so pace should not improve further during taper."""
    result = progress_training_pace(
        base_pace=300, current_pace=330, goal_pace=280,
        week_number=15, total_weeks=16, workout_type="tempo", phase="taper"
    )
    assert result == 300  # improvement = 0 due to multiplier


def test_progress_training_pace_race_type_allows_full_progression():
    """'race' workout type has target_progression=1.00, the highest of all types."""
    result = progress_training_pace(
        base_pace=300, current_pace=330, goal_pace=280,
        week_number=16, total_weeks=16, workout_type="race", phase="race_specific"
    )
    assert result < 300  # pace should have improved (lower seconds = faster)


# ---------------------------------------------------------------------------
# generate_week_sessions
# ---------------------------------------------------------------------------

def _sample_paces():
    return {"easy": 360, "long_run": 345, "tempo": 320, "race": 300, "interval": 310}


def test_generate_week_sessions_three_days_returns_three_sessions():
    sessions = generate_week_sessions(
        week_number=2,
        weekly_volume=40,
        long_run=15,
        training_days=3,
        available_days=["Mon", "Wed", "Sat"],
        phase="base",
        paces=_sample_paces(),
        current_pace=330,
        goal_pace=280,
        total_weeks=16,
    )
    assert len(sessions) == 3
    assert sessions[-1]["type"] == "long_run"
    assert sessions[-1]["day"] == "Sat"


def test_generate_week_sessions_five_days_returns_five_sessions():
    sessions = generate_week_sessions(
        week_number=2,
        weekly_volume=50,
        long_run=18,
        training_days=5,
        available_days=["Mon", "Tue", "Wed", "Fri", "Sun"],
        phase="build",
        paces=_sample_paces(),
        current_pace=330,
        goal_pace=280,
        total_weeks=16,
    )
    assert len(sessions) == 5
    total_distance = sum(s["distance_km"] for s in sessions)
    # sessions should roughly account for the weekly volume + long run
    # (loose check since long_run is passed separately, not carved from weekly_volume)
    assert total_distance > 0


def test_generate_week_sessions_quality_session_alternates_type():
    """Week 2 (even) should give 'tempo' as the quality session, per choose_quality_session."""
    sessions = generate_week_sessions(
        week_number=2,
        weekly_volume=40,
        long_run=15,
        training_days=3,
        available_days=["Mon", "Wed", "Sat"],
        phase="base",
        paces=_sample_paces(),
        current_pace=330,
        goal_pace=280,
        total_weeks=16,
    )
    assert sessions[1]["type"] == "tempo"