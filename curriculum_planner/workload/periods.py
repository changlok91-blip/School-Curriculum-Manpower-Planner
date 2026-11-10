"""Convert per-group weekly minutes to periods before any aggregation."""

from decimal import Decimal, InvalidOperation, localcontext

from .models import PeriodConversion


def normalized_minutes(value) -> Decimal:
    try:
        if isinstance(value, bool):
            raise ValueError("Minutes must be numeric")
        result = Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Minutes must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise ValueError("Minutes must be finite and non-negative")
    return result


def sum_minutes(values) -> Decimal:
    """Aggregate exact finite minutes without losing supplied decimal places."""
    values = list(values)
    if not values:
        return Decimal(0)
    with localcontext() as context:
        smallest_exponent = min(value.as_tuple().exponent for value in values)
        largest_position = max(value.adjusted() for value in values)
        context.prec = max(28, largest_position - smallest_exponent + 1
                           + len(str(len(values))) + 1)
        return sum(values, Decimal(0))


def convert_minutes(minimum_weekly_minutes, period_duration_minutes) -> PeriodConversion:
    minimum = normalized_minutes(minimum_weekly_minutes)
    duration = normalized_minutes(period_duration_minutes)
    if duration <= 0:
        raise ValueError("Period duration must be positive")
    # Ceiling the exact rational avoids rounding a value just above a period
    # boundary down to that boundary under Decimal's default precision.
    minimum_n, minimum_d = minimum.as_integer_ratio()
    duration_n, duration_d = duration.as_integer_ratio()
    numerator = minimum_n * duration_d
    denominator = minimum_d * duration_n
    required = (numerator + denominator - 1) // denominator
    with localcontext() as context:
        context.prec = max(28, len(minimum.as_tuple().digits),
                           len(duration.as_tuple().digits) + len(str(required))) + abs(
                               minimum.as_tuple().exponent - duration.as_tuple().exponent) + 2
        scheduled = required * duration
        excess = scheduled - minimum
    return PeriodConversion(required, scheduled, excess)
