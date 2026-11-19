"""World mode's calendar: the date a save is on, from its turn (one per time of day since the save began).

Every save starts on Monday 18 November. The calendar is a real one (months of their own lengths, leap years), anchored
on 2024, a year when 18 November was a Monday, so a save's weeks still run Monday to Sunday from its first day and
every weekday rule (haunts, events) means what it always has. The year itself is the save's own: Year 1 until the
first 1 January, then Year 2, and so on. Seasons and holidays build on `date_of` and `month_day`.
"""
import datetime

START = datetime.date(2024, 11, 18)  # a Monday: day 0 of every save
TIMES = 4  # times of day (WorldSave.TIMES)
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
SEASONS = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Spring", 4: "Spring", 5: "Spring", 6: "Summer", 7: "Summer",
           8: "Summer", 9: "Autumn", 10: "Autumn", 11: "Autumn"}  # by month, the northern hemisphere's


def day_of(turn):
    """The day the turn falls on, counting from 0 (the save's first)."""
    return turn // TIMES


def date_of(turn):
    """The calendar date the turn falls on."""
    return START + datetime.timedelta(days=day_of(turn))


def week_of(turn):
    """The week the turn falls in, counting from 0: weeks run Monday to Sunday."""
    return day_of(turn) // 7


def weekday_of(turn):
    """0 (Monday) to 6 (Sunday)."""
    return date_of(turn).weekday()


def year_of(turn):
    """The save's year: 1 until its first 1 January."""
    return date_of(turn).year - START.year + 1


def month_day(turn):
    """"MM-DD", for events on a date (a holiday): "12-25"."""
    found = date_of(turn)
    return f"{found.month:02}-{found.day:02}"


def season_of(turn):
    return SEASONS[date_of(turn).month]


def date_label(turn):
    """"Monday 18 November"."""
    found = date_of(turn)
    return f"{DAYS[found.weekday()]} {found.day} {MONTHS[found.month - 1]}"


def full_label(turn):
    """"Monday 18 November, Year 1"."""
    return f"{date_label(turn)}, Year {year_of(turn)}"


def short_label(turn):
    """"18 November": a day in the week's calendar, its weekday shown beside it."""
    found = date_of(turn)
    return f"{found.day} {MONTHS[found.month - 1]}"
