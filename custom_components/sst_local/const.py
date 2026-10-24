from datetime import timedelta

DOMAIN = "sst_local"
SCAN_INTERVAL = timedelta(seconds=30)

CONF_HOST = "host"
CONF_PORT = "port"
CONF_NAME = "name"

MIN_MANUAL_TEMP = 12
MAX_MANUAL_TEMP = 45
MIN_VACATION_TEMP = 5
MAX_VACATION_TEMP = 12

# Периоды расписания: ключ -> (название, дни недели, пн = 0)
PERIOD_WEEKDAYS = "weekdays"
PERIOD_WEEKEND = "weekend"
PERIODS: dict[str, tuple[str, range]] = {
    PERIOD_WEEKDAYS: ("Будни", range(0, 5)),
    PERIOD_WEEKEND: ("Выходные", range(5, 7)),
}

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_GET_SCHEDULE = "get_schedule"
ATTR_PERIOD = "period"
ATTR_POINTS = "points"
ATTR_TIME = "time"
