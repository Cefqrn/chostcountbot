from __future__ import annotations

from post import PostContent

from datetime import date, timedelta
from typing import NamedTuple

DAY = timedelta(1)


class Day(NamedTuple):
    date: date
    total: int
    post_id: int

    @property
    def formatted_date(self) -> str:
        return self.date.isoformat()

    @staticmethod
    def from_dict(d: dict[str, str]) -> Day:
        return Day(
            date=date.fromisoformat(d["date"]),
            total=int(d["total"]),
            post_id=int(d["post_id"])
        )

    def to_dict(self) -> dict[str, str]:
        return dict(
            date=self.date.isoformat(),
            total=str(self.total),
            post_id=str(self.post_id)
        )


def format_ratio(ratio: float) -> str:
    return f"{abs(ratio):.2%} {'more' if ratio >= 0 else 'less'}"


def get_post_url(project_name: str, day: Day):
    return f"/{project_name}/post/{day.post_id}-{day.formatted_date}"


def get_final_post_content(
    project_name: str,
    data: dict[date, Day],
    post_date: date
) -> PostContent:
    current_day = data[post_date]

    today_count = current_day.total - data[post_date - DAY].total

    # same day last week post count
    last_week_count = data[post_date - 7*DAY].total - data[post_date - 8*DAY].total
    last_week_ratio = (today_count - last_week_count) / last_week_count

    # post count for the past week (same day last week to post_date, excluded)
    average = (data[post_date - DAY].total - data[post_date - 8*DAY].total) / 7
    average_ratio = (today_count - average) / average

    last_week_post_url = get_post_url(project_name, data[post_date - 7*DAY])

    return PostContent(
        headline=current_day.formatted_date,
        body=(
            f"there have been {today_count} posts today\n\n"
            f"that's {format_ratio(last_week_ratio)} than [last week's count]({last_week_post_url}) and {format_ratio(average_ratio)} than the past week's average, {average:.2f}"
        )
    )
