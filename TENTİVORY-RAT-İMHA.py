# -*- coding: utf-8 -*-
"""
Asenkron versiyon: asyncio + aiohttp ile çalışır.
- Kullanıcı girdileri regex ile doğrulanır.
- 429 Rate Limit durumunda Retry-After başlığına göre yeniden deneme yapılır.
- Discord webhook'ları için GET/POST/DELETE işlemleri asenkron olarak yapılır.
- Telegram tokenları için getMe ve deleteWebhook çağrıları yapılır (bot token'larını Telegram API üzerinden tamamen iptal etmek mümkün değildir; bu araç bot ile bağlantıyı koparmayı dener).

Not: Gerçek tahribat yapmadan önce --dry-run modu veya kullanıcı onayı eklemeyi düşünün.
"""
from __future__ import annotations

import asyncio
import re
import sys
import time
from typing import List, Tuple, Optional

import aiohttp
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

console = Console()

# Regex doğrulamaları
DISCORD_WEBHOOK_RE = re.compile(
    r"^https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+/?$",
    re.IGNORECASE,
)
TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{35,}$")

# Genel ayarlar
MAX_RETRIES = 5
RETRY_BACKOFF = 1.5  # exponential backoff multiplier


def mask_secret(s: str, prefix: int = 6, suffix: int = 4) -> str:
    if not s:
        return ""
    if len(s) <= prefix + suffix:
        return "*" * len(s)
    return f"{s[:prefix]}...{s[-suffix:]}"


async def request_with_retry(
    session: aiohttp.ClientSession,
    method: str,
    url: str,
    max_retries: int = MAX_RETRIES,
    **kwargs,
) -> aiohttp.ClientResponse:
    """Yapılan istekte 429 gelirse Retry-After başlığına göre yeniden dener.

    Döner: aiohttp.ClientResponse (kullanıcı kodu response.status ve .text() veya .json() kullanmalı)
    Hata durumunda istisna yükselir.
    """
    attempt = 0
    backoff = 1.0
    while True:
        attempt += 1
        try:
            async with session.request(method, url, **kwargs) as resp:
                if resp.status == 429:
                    # Rate limited, bak Retry-After başlığı
                    ra = resp.headers.get("Retry-After")
                    wait = None
                    if ra is not None:
                        try:
                            # Retry-After bazen saniye, bazen tarih olabilir. Öncelikle integer olarak dene.
                            wait = int(float(ra))
                        except Exception:
                            try:
                                # tarih formatıysa hesapla
                                retry_ts = time.mktime(aiohttp.helpers.parse_http_date(ra))
                                wait = max(0, int(retry_ts - time.time()))
                            except Exception:
                                wait = None
                    if wait is None:
                        # fallback exponential backoff
                        wait = int(backoff)
                    console.print(f"[yellow]429 Rate limited. Bekleniyor: {wait} saniye (deneme {attempt}/{max_retries})[/yellow]")
                    await asyncio.sleep(wait)
                    backoff *= RETRY_BACKOFF
                    if attempt >= max_retries:
                        # return the 429 response so caller can inspect
                        return resp
                    continue
                # diğer durumlar için doğrudan döndür (başarılı ya da hata)
                return resp
        except aiohttp.ClientError as e:
            console.print(f"[red]Ağ hatası: {e} (deneme {attempt}/{max_retries})[/red]")
            if attempt >= max_retries:
                raise
            await asyncio.sleep(backoff)
            backoff *= RETRY_BACKOFF


# --- Discord işlemleri ---
async def get_discord_info(session: aiohttp.ClientSession, url: str) -> Tuple[bool, Optional[dict]]:
    """Discord webhook URL'sinin geçerli olup olmadığını kontrol eder ve webhook meta bilgisini döner."""
    try:
        resp = await request_with_retry(session, "GET", url)
        if resp.status == 200:
            data = await resp.json()
            return True, data
        return False, None
    except Exception as e:
        console.print(f"[red]Discord bilgi alınamadı: {e}[/red]")
        return False, None


async def spam_discord_webhook(session: aiohttp.ClientSession, url: str, content: str = "[!] TENTI IMHA TEST") -> Tuple[bool, str]:
    try:
        payload = {"content": content}
        resp = await request_with_retry(session, "POST", url, json=payload)
        txt = await resp.text()
        if resp.status in (200, 204):
            return True, "sent"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


async def nuke_discord_webhook(session: aiohttp.ClientSession, url: str) -> Tuple[bool, str]:
    """Webhook'u siler (DELETE)."""
    try:
        resp = await request_with_retry(session, "DELETE", url)
        txt = await resp.text()
        if resp.status in (200, 204):
            return True, "deleted"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


# --- Telegram işlemleri ---
async def get_telegram_info(session: aiohttp.ClientSession, token: str) -> Tuple[bool, Optional[dict]]:
    api = f"https://api.telegram.org/bot{token}/getMe"
    try:
        resp = await request_with_retry(session, "GET", api)
        txt = await resp.text()
        if resp.status == 200:
            try:
                data = await resp.json()
                if data.get("ok"):
                    return True, data
            except Exception:
                return False, None
        return False, None
    except Exception as e:
        console.print(f"[red]Telegram bilgi alınamadı: {e}[/red]")
        return False, None


async def nuke_telegram_bot(session: aiohttp.ClientSession, token: str) -> Tuple[bool, str]:
    """Telegram'da botun webhook'unu silmeye çalışır. (Token'ı iptal etmek Telegram API ile mümkün değildir.)"""
    api = f"https://api.telegram.org/bot{token}/deleteWebhook"
    try:
        resp = await request_with_retry(session, "POST", api)
        txt = await resp.text()
        if resp.status == 200:
            try:
                data = await resp.json()
                if data.get("ok"):
                    return True, "webhook_deleted"
                return False, f"api_error: {data}"
            except Exception:
                return False, f"non-json-response: {txt}"
        return False, f"status={resp.status} body={txt}"
    except Exception as e:
        return False, str(e)


# --- Yardımcılar ---
def is_valid_discord_webhook(url: str) -> bool:
    return bool(DISCORD_WEBHOOK_RE.match(url.strip()))


def is_valid_telegram_token(token: str) -> bool:
    return bool(TELEGRAM_TOKEN_RE.match(token.strip()))


async def handle_manual_discord(session: aiohttp.ClientSession) -> None:
    console.print("\n[bold blue][⇒] 1 NUMARALI ODA AÇILDI: Manuel Discord Webhook İmha[/bold blue]")
    url = input("Discord Webhook URL girin: ").strip()
    if not is_valid_discord_webhook(url):
        console.print("[red]Geçersiz Discord webhook formatı.[/red]")
        return
    ok, info = await get_discord_info(session, url)
    if not ok:
        console.print("[red]Webhook doğrulanamadı veya erişilemedi.[/red]")
        return
    onay = input("\nBu Tenti RAT iletişim kanalı imha edilsin mi? (E/H): ").strip().lower()
    if onay == "e":
        s_ok, s_msg = await spam_discord_webhook(session, url)
        console.print(f"[cyan]Spam sonucu:[/cyan] {s_ok} {s_msg}")
        n_ok, n_msg = await nuke_discord_webhook(session, url)
        console.print(f"[cyan]Nuke sonucu:[/cyan] {n_ok} {n_msg}")
    else:
        console.print("[yellow]İptal edildi.[/yellow]")


async def handle_manual_telegram(session: aiohttp.ClientSession) -> None:
    console.print("\n[bold purple][⇒] 2 NUMARALI ODA AÇILDI: Manuel Telegram Token İmha[/bold purple]")
    token = input("Tenti RAT Bot Token girin: ").strip()
    if not is_valid_telegram_token(token):
        console.print("[red]Geçersiz Telegram token formatı.[/red]")
        return
    ok, info = await get_telegram_info(session, token)
    if not ok:
        console.print("[red]Token doğrulanamadı veya erişilemedi.[/red]")
        return
    onay = input("\nSaldırganın bu bot üzerindeki veri bağı koparılsın mı? (E/H): ").strip().lower()
    if onay == "e":
        n_ok, n_msg = await nuke_telegram_bot(session, token)
        console.print(f"[cyan]Nuke sonucu:[/cyan] {n_ok} {n_msg}")
    else:
        console.print("[yellow]İptal edildi.[/yellow]")


async def handle_auto(session: aiohttp.ClientSession) -> None:
    console.print("\n[bold yellow][⇒] 3 NUMARALI LABORATUVAR AÇILDI: Akıllı Kod Deşifresi[/bold yellow]")
    # auto_extractor fonksiyonunun senkron olduğunu varsayıyoruz; eğer asenkron ise uygun şekilde çağrın
    try:
        extracted = auto_extractor()
    except Exception as e:
        console.print(f"[red]Otomatik deşifre hatası: {e}[/red]")
        return
    if not isinstance(extracted, (list, tuple)):
        # beklenen: (discords, telegrams)
        console.print("[red]auto_extractor beklenmeyen sonuç döndürdü.[/red]")
        return
    discords, telegrams = extracted

    tasks = []
    sem = asyncio.Semaphore(8)

    async def _nuke_d(durl: str):
        async with sem:
            if not is_valid_discord_webhook(durl):
                console.print(f"[yellow]Atlandı (geçersiz): {mask_secret(durl)}[/yellow]")
                return (durl, False, "invalid")
            ok, info = await get_discord_info(session, durl)
            if not ok:
                return (durl, False, "not_found")
            n_ok, n_msg = await nuke_discord_webhook(session, durl)
            return (durl, n_ok, n_msg)

    async def _nuke_t(tkn: str):
        async with sem:
            if not is_valid_telegram_token(tkn):
                console.print(f"[yellow]Atlandı (geçersiz): {mask_secret(tkn)}[/yellow]")
                return (tkn, False, "invalid")
            ok, info = await get_telegram_info(session, tkn)
            if not ok:
                return (tkn, False, "not_found")
            n_ok, n_msg = await nuke_telegram_bot(session, tkn)
            return (tkn, n_ok, n_msg)

    for d in discords:
        tasks.append(asyncio.create_task(_nuke_d(d)))
    for t in telegrams:
        tasks.append(asyncio.create_task(_nuke_t(t)))

    if not tasks:
        console.print("[yellow][!] İnceleme tamamlandı: Metin içerisinde Tenti RAT izine rastlanmadı.[/yellow]")
        return

    for fut in asyncio.as_completed(tasks):
        durl, ok, msg = await fut
        if ok:
            console.print(f"[green]Başarılı:[/green] {mask_secret(durl)} -> {msg}")
        else:
            console.print(f"[red]Başarısız:[/red] {mask_secret(durl)} -> {msg}")


async def main_async() -> None:
    console.print(Panel.fit(
        "[bold red]💥 TENTI RAT WEBHOOK & TOKEN İMHA SİSTEMİ v2.0 💥[/bold red]\n"
        "[bold blue]Kolay Kullanım Siber Savunma ve C2 Hattı Çökertme Paneli[/bold blue]",
        border_style="red"
    ))

    console.print("[bold cyan][?] Hangi numarayı açmak istiyorsunuz? Sayıyı yazıp ENTER'a basın:[/bold cyan]\n")
    console.print("[bold magenta][1] NUMARA[/bold magenta] -> [bold white]Manuel Discord İmha Odası[/bold white]")
    console.print("[bold magenta][2] NUMARA[/bold magenta] -> [bold white]Manuel Telegram İmha Odası[/bold white]")
    console.print("[bold magenta][3] NUMARA[/bold magenta] -> [bold white]Akıllı Kod Deşifre & Toplu İmha Laboratuvarı[/bold white]\n")

    secim = input("Açmak istediğiniz numara (1 / 2 / 3): ").strip()

    async with aiohttp.ClientSession() as session:
        if secim == "1":
            await handle_manual_discord(session)
        elif secim == "2":
            await handle_manual_telegram(session)
        elif secim == "3":
            await handle_auto(session)
        else:
            console.print("[bold red][-] Geçersiz numara! Lütfen sadece 1, 2 veya 3 yazın.[/bold red]")


def main() -> int:
    try:
        asyncio.run(main_async())
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Kullanıcı tarafından iptal edildi.[/yellow]")
        return 1
    except Exception as exc:
        console.print(f"[red]Beklenmeyen hata: {exc}[/red]")
        return 2


if __name__ == "__main__":
    sys.exit(main())
