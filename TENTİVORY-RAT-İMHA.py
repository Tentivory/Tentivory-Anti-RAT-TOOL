# Copyright (c) 2026 Tentivory — All Rights Reserved

from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import Optional, Tuple

import aiohttp
from rich.console import Console
from rich.panel import Panel

console = Console()

DISCORD_WEBHOOK_RE = re.compile(
    r"^https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+/?$",
    re.IGNORECASE,
)
TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{35,}$")

MAX_RETRIES = 5
RETRY_BACKOFF = 1.5


def mask_secret(s: str, prefix: int = 6, suffix: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= prefix + suffix:
        return "*" * len(s)
    return f"{s[:prefix]}...{s[-suffix:]}"


async def request_with_retry(
    session: aiohttp.ClientSession, method: str, url: str, max_retries: int = MAX_RETRIES, **kwargs
) -> aiohttp.ClientResponse:
    attempt = 0
    backoff = 1.0
    while True:
        attempt += 1
        try:
            async with session.request(method, url, **kwargs) as resp:
                if resp.status == 429:
                    ra = resp.headers.get("Retry-After")
                    wait: Optional[int] = None
                    if ra is not None:
                        try:
                            wait = int(float(ra))
                        except Exception:
                            try:
                                retry_ts = time.mktime(aiohttp.helpers.parse_http_date(ra))
                                wait = max(0, int(retry_ts - time.time()))
                            except Exception:
                                wait = None
                    if wait is None:
                        wait = int(backoff)
                    console.print(f"[yellow]Rate limited (429). Waiting {wait}s (attempt {attempt}/{max_retries})[/yellow]")
                    await asyncio.sleep(wait)
                    backoff *= RETRY_BACKOFF
                    if attempt >= max_retries:
                        return resp
                    continue
                return resp
        except aiohttp.ClientError as e:
            console.print(f"[red]Network error: {e} (attempt {attempt}/{max_retries})[/red]")
            if attempt >= max_retries:
                raise
            await asyncio.sleep(backoff)
            backoff *= RETRY_BACKOFF


async def get_discord_info(session: aiohttp.ClientSession, url: str) -> Tuple[bool, Optional[dict]]:
    try:
        resp = await request_with_retry(session, "GET", url)
        if resp.status == 200:
            return True, await resp.json()
        return False, None
    except Exception as e:
        console.print(f"[red]Failed to fetch Discord webhook info: {e}[/red]")
        return False, None


async def spam_discord_webhook(session: aiohttp.ClientSession, url: str, content: str = "[TEST] Tentivory") -> Tuple[bool, str]:
    try:
        resp = await request_with_retry(session, "POST", url, json={"content": content})
        txt = await resp.text()
        if resp.status in (200, 204):
            return True, "sent"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


async def nuke_discord_webhook(session: aiohttp.ClientSession, url: str) -> Tuple[bool, str]:
    try:
        resp = await request_with_retry(session, "DELETE", url)
        txt = await resp.text()
        if resp.status in (200, 204):
            return True, "deleted"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


async def get_telegram_info(session: aiohttp.ClientSession, token: str) -> Tuple[bool, Optional[dict]]:
    api = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = await request_with_retry(session, "GET", api)
        if resp.status == 200:
            data = await resp.json()
            if data.get("ok"):
                return True, data
        return False, None
    except Exception as e:
        console.print(f"[red]Failed to fetch Telegram info: {e}[/red]")
        return False, None


async def nuke_telegram_bot(session: aiohttp.ClientSession, token: str) -> Tuple[bool, str]:
    api = f"https://api.telegram.org/bot{token}/deleteWebhook"
    try:
        resp = await request_with_retry(session, "POST", api)
        txt = await resp.text()
        if resp.status == 200:
            data = await resp.json()
            if data.get("ok"):
                return True, "webhook_deleted"
            return False, f"api_error: {data}"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


def is_valid_discord_webhook(url: str) -> bool:
    return bool(DISCORD_WEBHOOK_RE.match(url.strip()))


def is_valid_telegram_token(token: str) -> bool:
    return bool(TELEGRAM_TOKEN_RE.match(token.strip()))


async def handle_manual_discord(session: aiohttp.ClientSession) -> None:
    console.print("\n1) Manual Discord webhook review and removal")
    url = input("Discord webhook URL: ").strip()
    if not is_valid_discord_webhook(url):
        console.print("[red]Invalid Discord webhook format.[/red]")
        return
    ok, info = await get_discord_info(session, url)
    if not ok:
        console.print("[red]Webhook not reachable or invalid.[/red]")
        return
    console.print(f"Target: {mask_secret(url, 18, 8)}")
    if input("Confirm removal? (E/H): ").strip().lower() != "e":
        console.print("[yellow]Cancelled.[/yellow]")
        return
    s_ok, s_msg = await spam_discord_webhook(session, url)
    console.print(f"Test send: {s_ok} {s_msg}")
    n_ok, n_msg = await nuke_discord_webhook(session, url)
    console.print(f"Removal: {n_ok} {n_msg}")


async def handle_manual_telegram(session: aiohttp.ClientSession) -> None:
    console.print("\n2) Manual Telegram bot review and removal")
    token = input("Bot token: ").strip()
    if not is_valid_telegram_token(token):
        console.print("[red]Invalid Telegram token format.[/red]")
        return
    ok, info = await get_telegram_info(session, token)
    if not ok:
        console.print("[red]Token not valid or unreachable.[/red]")
        return
    console.print(f"Target: {mask_secret(token)}")
    if input("Confirm removal? (E/H): ").strip().lower() != "e":
        console.print("[yellow]Cancelled.[/yellow]")
        return
    n_ok, n_msg = await nuke_telegram_bot(session, token)
    console.print(f"Removal: {n_ok} {n_msg}")


async def handle_auto(session: aiohttp.ClientSession) -> None:
    console.print("\n3) Automatic extractor and bulk response")
    try:
        extracted = auto_extractor()
    except Exception as e:
        console.print(f"[red]Auto extractor failed: {e}[/red]")
        return
    if not isinstance(extracted, (list, tuple)) or len(extracted) != 2:
        console.print("[red]Auto extractor returned unexpected result.[/red]")
        return
    discords, telegrams = extracted
    sem = asyncio.Semaphore(8)

    async def _nuke_d(durl: str):
        async with sem:
            if not is_valid_discord_webhook(durl):
                return durl, False, "invalid"
            ok, _ = await get_discord_info(session, durl)
            if not ok:
                return durl, False, "not_found"
            return durl, *await nuke_discord_webhook(session, durl)

    async def _nuke_t(tkn: str):
        async with sem:
            if not is_valid_telegram_token(tkn):
                return tkn, False, "invalid"
            ok, _ = await get_telegram_info(session, tkn)
            if not ok:
                return tkn, False, "not_found"
            return tkn, *await nuke_telegram_bot(session, tkn)

    tasks = [asyncio.create_task(_nuke_d(d)) for d in discords] + [asyncio.create_task(_nuke_t(t)) for t in telegrams]

    if not tasks:
        console.print("[yellow]No targets found.[/yellow]")
        return

    for fut in asyncio.as_completed(tasks):
        target, ok, msg = await fut
        if ok:
            console.print(f"[green]OK:[/green] {mask_secret(target)} -> {msg}")
        else:
            console.print(f"[red]FAILED:[/red] {mask_secret(target)} -> {msg}")


async def main_async() -> None:
    console.print(Panel.fit("TENTIVORY - Webhook & Token Response Tool v2.0", border_style="blue"))
    console.print("Available actions:")
    console.print("1) Manual Discord webhook review and removal")
    console.print("2) Manual Telegram bot review and removal")
    console.print("3) Automatic extractor and bulk response")

    choice = input("Select an action (1/2/3): ").strip()

    async with aiohttp.ClientSession() as session:
        if choice == "1":
            await handle_manual_discord(session)
        elif choice == "2":
            await handle_manual_telegram(session)
        elif choice == "3":
            await handle_auto(session)
        else:
            console.print("[red]Invalid selection.[/red]")


def main() -> int:
    try:
        asyncio.run(main_async())
        return 0
    except KeyboardInterrupt:
        console.print("[yellow]Interrupted by user.[/yellow]")
        return 1
    except Exception as exc:
        console.print(f"[red]Unexpected error: {exc}[/red]")
        return 2


if __name__ == "__main__":
    sys.exit(main())
