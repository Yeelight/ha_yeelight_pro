"""Constants for the Yeelight Pro integration."""

from collections.abc import Mapping

DOMAIN = "yeelight_pro"

# 连接模式
CONNECTION_MODE_CLOUD = "cloud"
CONNECTION_MODE_PRIVATE = "private"
CONNECTION_MODE_LAN = "lan"

# 配置键
CONF_CONNECTION_MODE = "connection_mode"
CONF_CLOUD_DOMAIN = "cloud_domain"
CONF_CLOUD_REGION = "cloud_region"
CONF_PRIVATE_DOMAIN = "private_domain"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRES_IN = "token_expires_in"
CONF_TOKEN_TYPE = "token_type"
CONF_HOUSE_ID = "house_id"
CONF_HOUSE_NAME = "house_name"
CONF_ACCOUNT_USER_ID = "account_user_id"
CONF_ACCOUNT_USERNAME = "account_username"
CONF_CLOUD_AUTH_METHOD = "cloud_auth_method"
CONF_OPEN_API_CLIENT_ID = "open_api_client_id"
CONF_OPEN_API_CLIENT_SECRET = "open_api_client_secret"
CONF_SCAN_LOGIN_DEVICE = "scan_login_device"
CONF_SCAN_LOGIN_QRCODE = "scan_login_qrcode"
CONF_SCAN_LOGIN_REFRESH = "scan_login_refresh"

CLOUD_AUTH_METHOD_ACCESS_TOKEN = "access_token"
CLOUD_AUTH_METHOD_SCAN_LOGIN = "scan_login"

CLOUD_REGION_CN = "cn"
CLOUD_REGION_SG = "sg"
CLOUD_REGION_US = "us"
CLOUD_REGION_EU = "de"
DEFAULT_CLOUD_REGION = CLOUD_REGION_CN
CLOUD_REGIONS = [
    CLOUD_REGION_CN,
    CLOUD_REGION_SG,
    CLOUD_REGION_US,
    CLOUD_REGION_EU,
]
CLOUD_REGION_BASE_DOMAINS = {
    CLOUD_REGION_CN: "https://api.yeelight.com",
    CLOUD_REGION_SG: "https://api-sg.yeelight.com",
    CLOUD_REGION_US: "https://api-us.yeelight.com",
    CLOUD_REGION_EU: "https://api-de.yeelight.com",
}

# 选项键
CONF_SCAN_INTERVAL = "scan_interval"
CONF_DEBUG_MODE = "debug_mode"
CONF_HIDE_UNKNOWN_ENTITIES = "hide_unknown_entities"
CONF_TOPOLOGY_CHANGE_REPAIRS = "topology_change_repairs"
CONF_DEVICE_IMPORT_FILTER = "device_import_filter"
CONF_DEVICE_IMPORT_FILTER_ENABLED = "device_import_filter_enabled"
CONF_DEVICE_IMPORT_FILTER_MODE = "device_import_filter_mode"
CONF_DEVICE_IMPORT_FILTER_INCLUDE_CATEGORIES = "device_import_filter_include_categories"
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_CATEGORIES = "device_import_filter_exclude_categories"
CONF_DEVICE_IMPORT_FILTER_INCLUDE_TYPES = "device_import_filter_include_types"
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_TYPES = "device_import_filter_exclude_types"
CONF_DEVICE_IMPORT_FILTER_INCLUDE_ROOMS = "device_import_filter_include_rooms"
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_ROOMS = "device_import_filter_exclude_rooms"
CONF_DEVICE_IMPORT_FILTER_INCLUDE_GATEWAYS = "device_import_filter_include_gateways"
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_GATEWAYS = "device_import_filter_exclude_gateways"
CONF_DEVICE_IMPORT_FILTER_INCLUDE_PRODUCT_IDS = (
    "device_import_filter_include_product_ids"
)
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_PRODUCT_IDS = (
    "device_import_filter_exclude_product_ids"
)
CONF_DEVICE_IMPORT_FILTER_INCLUDE_DEVICES = "device_import_filter_include_devices"
CONF_DEVICE_IMPORT_FILTER_EXCLUDE_DEVICES = "device_import_filter_exclude_devices"
CONF_DEVICE_IMPORT_FILTER_PICKER = "device_import_filter_picker"
CONF_LIVE_UPDATES = "live_updates"
CONF_LOCAL_GATEWAY_CONTROL = "local_gateway_control"
CONF_LOCAL_GATEWAY_HOST = "local_gateway_host"
CONF_LOCAL_GATEWAY_PORT = "local_gateway_port"
CONF_LOCAL_GATEWAY_PRODUCT_ID = "local_gateway_product_id"

# LAN 模式配置键
CONF_LAN_GATEWAY_IP = "lan_gateway_ip"
CONF_LAN_GATEWAY_PORT = "lan_gateway_port"
CONF_LAN_GATEWAY_PRODUCT_ID = "lan_gateway_product_id"
LAN_GATEWAY_PRODUCT_ID_GATEWAY = 1
LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL = 2
LAN_GATEWAY_PRODUCT_IDS = [
    LAN_GATEWAY_PRODUCT_ID_GATEWAY,
    LAN_GATEWAY_PRODUCT_ID_WIFI_PANEL,
]

# 默认域名
DEFAULT_CLOUD_DOMAIN = "https://api.yeelight.com/apis/iot"
DEFAULT_PRIVATE_DOMAIN = "https://private.example"
DEFAULT_HOUSE_NAME = "易来家庭"

# 默认配置
DEFAULT_SCAN_INTERVAL = 30  # 秒
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 300
DEFAULT_DEBUG_MODE = False
DEFAULT_HIDE_UNKNOWN_ENTITIES = True
DEFAULT_TOPOLOGY_CHANGE_REPAIRS = True
DEFAULT_LIVE_UPDATES = False
DEFAULT_LOCAL_GATEWAY_CONTROL = False
DEFAULT_LOCAL_GATEWAY_HOST = ""
DEFAULT_LOCAL_GATEWAY_PORT = 65443
DEFAULT_LAN_GATEWAY_IP = ""
DEFAULT_LAN_GATEWAY_PORT = 65443
DEFAULT_REQUEST_TIMEOUT = 10  # 秒
DEFAULT_THING_MANAGE_PAGE_SIZE = 200
DEFAULT_PRODUCT_SCHEMA_BATCH_SIZE = 50

# Home Assistant platforms loaded by the current Yeelight Pro integration.
PLATFORMS = [
    "binary_sensor",
    "button",
    "climate",
    "cover",
    "event",
    "fan",
    "light",
    "number",
    "select",
    "sensor",
    "switch",
]

def get_enabled_platforms(options: Mapping | None = None) -> list[str]:
    """根据配置选项返回应加载的平台列表."""
    return list(PLATFORMS)

# 事件类型
DEVICE_EVENT_TYPE = f"{DOMAIN}_device_event"
ATTR_SOURCE_DEVICE_ID = "source_device_id"
ATTR_COMPONENT_ID = "component_id"
ATTR_EVENT_TYPE = "event_type"
ATTR_EVENT_ATTRIBUTES = "event_attributes"
