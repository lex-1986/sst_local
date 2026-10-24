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
