"""Private push broadcast probe CLI safety tests."""

from __future__ import annotations

import pytest

from scripts.probe_private_push_broadcast import build_parser, _validate_args


def test_broadcast_probe_defaults_to_listen_only() -> None:
    """默认模式只监听，不应写设备。"""
    args = build_parser().parse_args(
        [
            "--entry-title",
            "Yeelight Pro Private",
        ]
    )

    _validate_args(args)
    assert args.execute is False
    assert args.flip_restore is False
    assert args.listener_count == 2


def test_broadcast_probe_rejects_flip_restore_without_execute() -> None:
    """翻转恢复必须显式 execute，避免误触真实设备。"""
    with pytest.raises(SystemExit):
        _validate_args(
            build_parser().parse_args(
                [
                    "--entry-title",
                    "Yeelight Pro Private",
                    "--flip-restore",
                ]
            )
        )


def test_broadcast_probe_bounds_listener_count() -> None:
    """监听连接数量必须有上限，避免误触发服务端保护。"""
    with pytest.raises(SystemExit):
        _validate_args(
            build_parser().parse_args(
                [
                    "--entry-title",
                    "Yeelight Pro Private",
                    "--listener-count",
                    "5",
                ]
            )
        )
