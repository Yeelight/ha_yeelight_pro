"""Shared classification statuses and follow-up actions."""

ACTION_REGISTRY_REFRESH = "reload_or_refresh_ha_registry"
ACTION_SYNC_RUNTIME = "sync_or_reload_installed_runtime"
ACTION_NO_CODE_CHANGE = "no_code_change"
ACTION_INVESTIGATE_SOURCE_DATA = "investigate_source_data"
ACTION_FIX_PROJECTION = "fix_projection"

STATUS_OK = "ok"
STATUS_RUNTIME_DRIFT = "runtime_drift"
STATUS_REGISTRY_STALE = "registry_stale"
STATUS_SOURCE_DATA_LIMITED = "source_data_limited"
STATUS_PROJECTION_GAP = "projection_gap"
