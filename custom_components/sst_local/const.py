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

DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
WEEKDAYS = range(0, 5)

SERVICE_SET_SCHEDULE = "set_schedule"
SERVICE_GET_SCHEDULE = "get_schedule"
ATTR_DAYS = "days"
ATTR_POINTS = "points"
ATTR_TIME = "time"
