#!/usr/bin/env python3
"""
Class Conflict: Millionaire — 環境変数セットアップスクリプト

Usage:
    python scripts/setup_env.py          # 対話式セットアップ
    python scripts/setup_env.py --check  # 既存設定の検証のみ
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
ENV_EXAMPLE = PROJECT_ROOT / ".env.example"


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def test_api_connection(api_key: str) -> tuple[bool, str]:
    """Test the Mistral API key by listing available models."""
    try:
        from mistralai import Mistral
    except ImportError:
        return False, "mistralai パッケージが未インストールです。pip install mistralai を実行してください。"

    try:
        client = Mistral(api_key=api_key)
        models = client.models.list()
        model_ids = [m.id for m in models.data] if models.data else []
        has_small = any("mistral-small" in mid for mid in model_ids)
        has_large = any("mistral-large" in mid for mid in model_ids)
        if has_small and has_large:
            return True, f"接続成功 — {len(model_ids)} モデル利用可能 (mistral-small ✓, mistral-large ✓)"
        elif model_ids:
            return True, f"接続成功 — {len(model_ids)} モデル利用可能 (一部モデルが見つかりません)"
        else:
            return True, "接続成功 — モデル一覧は空ですがAPIキーは有効です"
    except Exception as e:
        return False, f"接続失敗 — {e}"


def check_env() -> bool:
    """Check current environment setup and report status."""
    print("=" * 50)
    print("  環境変数チェック")
    print("=" * 50)

    # Check .env file
    if ENV_FILE.exists():
        print(f"✓ .env ファイル: {ENV_FILE}")
        env = load_env_file(ENV_FILE)
    else:
        print(f"✗ .env ファイルが見つかりません: {ENV_FILE}")
        env = {}

    # Check MISTRAL_API_KEY
    api_key = env.get("MISTRAL_API_KEY") or os.environ.get("MISTRAL_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("✗ MISTRAL_API_KEY: 未設定")
        print("  → https://console.mistral.ai/ でAPIキーを取得してください")
        return False

    masked = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "****"
    print(f"✓ MISTRAL_API_KEY: {masked}")

    # Test connection
    print("\n接続テスト中...")
    ok, msg = test_api_connection(api_key)
    if ok:
        print(f"✓ {msg}")
    else:
        print(f"✗ {msg}")
    return ok


def interactive_setup():
    """Interactive .env setup wizard."""
    print("=" * 50)
    print("  Class Conflict: Millionaire セットアップ")
    print("=" * 50)

    # Load existing values
    existing = load_env_file(ENV_FILE) if ENV_FILE.exists() else {}

    current_key = existing.get("MISTRAL_API_KEY", "")
    if current_key and current_key != "your_api_key_here":
        masked = current_key[:4] + "..." + current_key[-4:] if len(current_key) > 8 else "****"
        print(f"\n現在のAPIキー: {masked}")
        resp = input("APIキーを変更しますか？ [y/N]: ").strip().lower()
        if resp != "y":
            print("既存の設定を維持します。")
            print("\n接続テスト中...")
            ok, msg = test_api_connection(current_key)
            print(f"  {'✓' if ok else '✗'} {msg}")
            return ok
    else:
        print("\nMistral APIキーが必要です。")
        print("取得先: https://console.mistral.ai/")

    # Get new key
    print()
    api_key = input("MISTRAL_API_KEY を入力: ").strip()
    if not api_key:
        print("キャンセルしました。")
        return False

    # Test before saving
    print("\n接続テスト中...")
    ok, msg = test_api_connection(api_key)
    print(f"  {'✓' if ok else '✗'} {msg}")

    if not ok:
        resp = input("\n接続に失敗しましたが、保存しますか？ [y/N]: ").strip().lower()
        if resp != "y":
            print("保存をキャンセルしました。")
            return False

    # Write .env
    existing["MISTRAL_API_KEY"] = api_key
    lines = [f"{k}={v}" for k, v in existing.items()]
    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"\n✓ {ENV_FILE} に保存しました。")
    return True


def main():
    parser = argparse.ArgumentParser(description="環境変数セットアップ")
    parser.add_argument("--check", action="store_true", help="既存設定の検証のみ")
    args = parser.parse_args()

    if args.check:
        ok = check_env()
    else:
        ok = interactive_setup()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
