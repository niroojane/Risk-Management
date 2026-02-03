"""Date utilities"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import List, Tuple


def split_date_range(
    start_date: datetime,
    end_date: datetime,
    chunk_months: int = 3
) -> List[Tuple[datetime, datetime]]:
    """Split a date range into chunks of specified months"""
    chunks = []
    current_start = start_date

    while current_start < end_date:
        current_end = min(
            current_start + relativedelta(months=chunk_months),
            end_date
        )
        chunks.append((current_start, current_end))
        current_start = current_end

    return chunks
