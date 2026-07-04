# Copyright (c) 2026 Tentivory — All Rights Reserved

from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import Optional, Tuple, List

import aiohttp
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DISCORD_WEBHOOK_RE = re.compile(
    r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+/?",
    re.IGNORECASE,
)
TELEGRAM_TOKEN_RE = re.compile(r"\d{5,}:[A-Za-z0-9_-]{35,}")

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


def auto_extract_from_file(file_path: str) -> Tuple[List[str], List[str]]:
    """Dosyadan Discord webhooks ve Telegram tokenlarını tespit et"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        discord_webhooks = DISCORD_WEBHOOK_RE.findall(content)
        telegram_tokens = TELEGRAM_TOKEN_RE.findall(content)
        return list(set(discord_webhooks)), list(set(telegram_tokens))
    except Exception as e:
        console.print(f"[red]Dosya okunurken hata: {e}[/red]")
        return [], []


def auto_extractor() -> Tuple[List[str], List[str]]:
    """Eksik fonksiyon - dosyadan otomatik tespit"""
    file_path = input("Kontrol edilecek dosya yolunu girin: ").strip()
    if not file_path:
        console.print("[red]Dosya yolu boş olamaz.[/red]")
        return [], []
    return auto_extract_from_file(file_path)


def auto_detect_from_terminal() -> Tuple[List[str], List[str]]:
    """Terminalde girilen metinden Discord webhooks ve Telegram tokenlarını tespit et"""
    console.print("\n[cyan]Terminale metni yapıştır veya yazıyı gir (Bitirmek için 'END' yazıp Enter'a bas):[/cyan]")
    
    lines = []
    while True:
        try:
            line = input()
            if line.strip().upper() == "END":
                break
            lines.append(line)
        except EOFError:
            break
    
    full_text = "\n".join(lines)
    
    # Discord webhooks tespit et
    discord_webhooks = DISCORD_WEBHOOK_RE.findall(full_text)
    discord_webhooks = list(set(discord_webhooks))  # Duplikatlari kaldır
    
    # Telegram tokenları tespit et
    telegram_tokens = TELEGRAM_TOKEN_RE.findall(full_text)
    telegram_tokens = list(set(telegram_tokens))  # Duplikatlari kaldır
    
    return discord_webhooks, telegram_tokens


async def handle_manual_discord(session: aiohttp.ClientSession) -> None:
    console.print("\n[bold cyan]1) Manual Discord webhook review and removal[/bold cyan]")
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
    console.print("\n[bold cyan]2) Manual Telegram bot review and removal[/bold cyan]")
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
    console.print("\n[bold cyan]3) Automatic extractor and bulk response[/bold cyan]")
    try:
        extracted = auto_extractor()
    except Exception as e:
        console.print(f"[red]Auto extractor failed: {e}[/red]")
        return
    if not isinstance(extracted, (list, tuple)) or len(extracted) != 2:
        console.print("[red]Auto extractor returned unexpected result.[/red]")
        return
    discords, telegrams = extracted
    
    if not discords and not telegrams:
        console.print("[yellow]Hiçbir Discord webhook veya Telegram token bulunamadı.[/yellow]")
        return
    
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


async def handle_terminal_scan(session: aiohttp.ClientSession) -> None:
    """4) Terminalde Discord webhooks ve Telegram tokenlarını otomatik tespit et"""
    console.print("\n[bold cyan]4) Terminal Scanner - Auto Detect Discord & Telegram[/bold cyan]")
    
    # Terminalde metni al
    discords, telegrams = auto_detect_from_terminal()
    
    if not discords and not telegrams:
        console.print("[yellow]Hiçbir Discord webhook veya Telegram token bulunamadı.[/yellow]")
        return
    
    # Sonuçları tablo formatında göster
    table = Table(title="[bold]Tespit Edilen Hedefler[/bold]", show_header=True, header_style="bold magenta")
    table.add_column("Tür", style="cyan")
    table.add_column("Değer (Maskelendi)", style="green")
    table.add_column("Durum", style="yellow")
    
    # Discord webhooks ekle
    for webhook in discords:
        is_valid = "✓ Geçerli" if is_valid_discord_webhook(webhook) else "✗ Geçersiz"
        table.add_row("Discord Webhook", mask_secret(webhook, 18, 8), is_valid)
    
    # Telegram tokenları ekle
    for token in telegrams:
        is_valid = "✓ Geçerli" if is_valid_telegram_token(token) else "✗ Geçersiz"
        table.add_row("Telegram Token", mask_secret(token), is_valid)
    
    console.print(table)
    console.print(f"\n[bold]Toplam Bulundu:[/bold] {len(discords)} Discord Webhook, {len(telegrams)} Telegram Token")
    
    # İşlem seçeneği
    choice = input("\nİşlem: [D]ile (D), [V]erify et (V), [S]pam (S), [İ]ptal (E): ").strip().lower()
    
    if choice == "e":
        console.print("[yellow]İşlem iptal edildi.[/yellow]")
        return
    
    if choice not in ("d", "v", "s"):
        console.print("[red]Geçersiz seçim.[/red]")
        return
    
    sem = asyncio.Semaphore(8)
    
    # Verify: Webhook ve tokenları kontrol et
    if choice == "v":
        console.print("\n[cyan]Doğrulama başlıyor...[/cyan]")
        
        async def verify_discord(url: str):
            async with sem:
                ok, _ = await get_discord_info(session, url)
                return ("Discord", url, ok)
        
        async def verify_telegram(token: str):
            async with sem:
                ok, _ = await get_telegram_info(session, token)
                return ("Telegram", token, ok)
        
        tasks = [asyncio.create_task(verify_discord(d)) for d in discords] + \
                [asyncio.create_task(verify_telegram(t)) for t in telegrams]
        
        for fut in asyncio.as_completed(tasks):
            typ, target, ok = await fut
            status = "[green]✓ Aktif[/green]" if ok else "[red]✗ Inaktif/Geçersiz[/red]"
            console.print(f"{typ}: {mask_secret(target)} -> {status}")
        return
    
    # Delete: Webhook ve tokenları sil
    elif choice == "d":
        confirm = input("[bold red]UYARI: Bu işlem geri döndürülemez! Devam? (E/H):[/bold red] ").strip().lower()
        if confirm != "e":
            console.print("[yellow]Silme işlemi iptal edildi.[/yellow]")
            return
        
        console.print("\n[cyan]Silme işlemi başlıyor...[/cyan]")
        
        async def nuke_d(url: str):
            async with sem:
                ok, msg = await nuke_discord_webhook(session, url)
                return ("Discord", url, ok, msg)
        
        async def nuke_t(token: str):
            async with sem:
                ok, msg = await nuke_telegram_bot(session, token)
                return ("Telegram", token, ok, msg)
        
        tasks = [asyncio.create_task(nuke_d(d)) for d in discords] + \
                [asyncio.create_task(nuke_t(t)) for t in telegrams]
        
        for fut in asyncio.as_completed(tasks):
            typ, target, ok, msg = await fut
            if ok:
                console.print(f"[green]✓ {typ}:[/green] {mask_secret(target)} -> {msg}")
            else:
                console.print(f"[red]✗ {typ}:[/red] {mask_secret(target)} -> {msg}")
    
    # Spam: Webhook'lara spam gönder
    elif choice == "s":
        confirm = input("[bold yellow]Spam bombardımanı başlat? (E/H):[/bold yellow] ").strip().lower()
        if confirm != "e":
            console.print("[yellow]Spam işlemi iptal edildi.[/yellow]")
            return
        
        console.print("\n[cyan]Spam gönderiliyor...[/cyan]")
        
        async def spam_d(url: str, count: int):
            async with sem:
                results = []
                for i in range(count):
                    ok, msg = await spam_discord_webhook(session, url, f"[SPAM {i+1}] Tentivory")
                    results.append(ok)
                return ("Discord", url, sum(results))
        
        tasks = [asyncio.create_task(spam_d(d, 5)) for d in discords]
        
        for fut in asyncio.as_completed(tasks):
            typ, target, sent = await fut
            console.print(f"[cyan]{typ}:[/cyan] {mask_secret(target)} -> {sent} mesaj gönderildi")


async def main_async() -> None:
    console.print(Panel.fit("TENTIVORY - Webhook & Token Response Tool v3.0 (FIXED)", border_style="blue"))
    console.print("\n[bold]Available actions:[/bold]")
    console.print("1) Manual Discord webhook review and removal")
    console.print("2) Manual Telegram bot review and removal")
    console.print("3) Automatic extractor and bulk response")
    console.print("4) Terminal Scanner - Auto Detect Discord & Telegram")
    console.print("")

    choice = input("Select an action (1/2/3/4): ").strip()

    async with aiohttp.ClientSession() as session:
        if choice == "1":
            await handle_manual_discord(session)
        elif choice == "2":
            await handle_manual_telegram(session)
        elif choice == "3":
            await handle_auto(session)
        elif choice == "4":
            await handle_terminal_scan(session)
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
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
