"""Yeelight Pro Open API node operation facade for the HTTP client."""

from __future__ import annotations

from .client_data_analytics import YeelightProDataAnalyticsMixin
from .client_node_lists import YeelightProNodeListMixin
from .client_node_properties import YeelightProNodePropertyMixin


class YeelightProNodeApiMixin(
    YeelightProDataAnalyticsMixin,
    YeelightProNodePropertyMixin,
    YeelightProNodeListMixin,
):
    """兼容旧导入路径的开放平台节点接口聚合 mixin."""
