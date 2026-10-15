
import jdatetime


def jalali_to_gregorian(date_string):
    """
    تبدیل تاریخ شمسی به تاریخ میلادی.

    نمونه ورودی:
        1405/05/08
        1405-05-08

    خروجی:
        datetime.date
    """

    if not date_string:
        return None

    try:
        date_string = str(date_string).strip()

        # پشتیبانی از / و -
        date_string = date_string.replace("-", "/")

        parts = date_string.split("/")

        if len(parts) != 3:
            return None

        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])

        jalali_date = jdatetime.date(
            year,
            month,
            day,
        )

        return jalali_date.togregorian()

    except (ValueError, TypeError):
        return None
