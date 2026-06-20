"""Private push control echo probe CLI tests."""

from __future__ import annotations

import pytest

from scripts.probe_private_push_control_echo import (
    _push_base_url,
    _token_from_file,
    build_parser,
    _validate_args,
)


def test_control_echo_probe_rejects_flip_restore_without_execute() -> None:
    """flip-restore 模式必须显式执行，避免误以为 dry-run 会写设备."""
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


def test_control_echo_probe_accepts_flip_restore_with_execute() -> None:
    """显式 execute 时可使用短暂翻转并恢复的诊断模式."""
    args = build_parser().parse_args(
        [
            "--entry-title",
            "Yeelight Pro Private",
            "--execute",
            "--flip-restore",
        ]
    )

    _validate_args(args)
    assert args.execute is True
    assert args.flip_restore is True


def test_control_echo_probe_accepts_split_listener_and_writer_tokens(tmp_path) -> None:
    """诊断脚本支持 listener/writer token 分离，便于模拟 App 写入、HA 监听."""
    listener = tmp_path / "listener.token"
    writer = tmp_path / "writer.token"
    listener.write_text("listener-token\n", encoding="utf-8")
    writer.write_text("writer-token\n", encoding="utf-8")

    args = build_parser().parse_args(
        [
            "--entry-title",
            "Yeelight Pro Private",
            "--listener-token-file",
            str(listener),
            "--writer-token-file",
            str(writer),
            "--writer-client-id",
            "dev",
        ]
    )

    _validate_args(args)
    assert args.listener_token_file == listener
    assert args.writer_token_file == writer
    assert args.writer_client_id == "dev"
    assert _token_from_file(listener, fallback="entry-token") == "listener-token"
    assert _token_from_file(writer, fallback="entry-token") == "writer-token"


def test_control_echo_probe_rejects_empty_token_file(tmp_path) -> None:
    """空 token 文件必须 fail-close，避免误用 entry token 得出错误结论."""
    token_file = tmp_path / "empty.token"
    token_file.write_text("\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        _token_from_file(token_file, fallback="entry-token")


def test_control_echo_probe_accepts_push_base_url_override() -> None:
    """诊断脚本允许临时指定 push endpoint，不需要改 HA 存储。"""
    args = build_parser().parse_args(
        [
            "--entry-title",
            "Yeelight Pro Private",
            "--push-base-url",
            "ws://192.168.1.202:7779/ws",
        ]
    )

    assert args.push_base_url == "ws://192.168.1.202:7779/ws"


def test_control_echo_probe_repairs_known_private_push_cross_route() -> None:
    """诊断脚本应与运行时一样修正 api-dev 到 api-test push 的错配。"""
    assert (
        _push_base_url(
            {
                "private_domain": "http://api-dev.yeedev.com",
                "private_push_domain": "ws://192.168.0.89:7779/ws",
            }
        )
        == "ws://192.168.1.202:7779/ws"
    )
