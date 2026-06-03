"""Constants for the Yeelight Pro integration."""

DOMAIN = "yeelight_pro"

# 连接模式
CONNECTION_MODE_CLOUD = "cloud"
CONNECTION_MODE_PRIVATE = "private"

# 配置键
CONF_CONNECTION_MODE = "connection_mode"
CONF_CLOUD_DOMAIN = "cloud_domain"
CONF_PRIVATE_DOMAIN = "private_domain"
CONF_ACCESS_TOKEN = "access_token"
CONF_HOUSE_ID = "house_id"

# 默认域名
DEFAULT_CLOUD_DOMAIN = "api.yeelight.com"
DEFAULT_PRIVATE_DOMAIN = "192.168.1.100:8080"

# 默认配置
DEFAULT_SCAN_INTERVAL = 30  # 秒
DEFAULT_REQUEST_TIMEOUT = 10  # 秒
DEFAULT_THING_MANAGE_PAGE_SIZE = 200
DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE = 50

# 支持的平台
PLATFORMS = [
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "event",
    "fan",
    "light",
    "lock",
    "number",
    "select",
    "sensor",
    "switch",
    "text",
    "vacuum",
]

# 事件类型
DEVICE_EVENT_TYPE = f"{DOMAIN}_device_event"
ATTR_SOURCE_DEVICE_ID = "source_device_id"
ATTR_COMPONENT_ID = "component_id"
ATTR_EVENT_TYPE = "event_type"
ATTR_EVENT_ATTRIBUTES = "event_attributes"
