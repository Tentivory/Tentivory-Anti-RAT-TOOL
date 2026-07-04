def main():
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
    
    if secim == "1":
        console.print("\n[bold blue][⇒] 1 NUMARALI ODA AÇILDI: Manuel Discord Webhook İmha[/bold blue]")
        url = input("Discord Webhook URL girin: ").strip()
        if get_discord_info(url):
            onay = input("\nBu Tenti RAT iletişim kanalı imha edilsin mi? (E/H): ").strip().lower()
            if onay == 'e':
                spam_discord_webhook(url)
                nuke_discord_webhook(url)
                
    elif secim == "2":
        console.print("\n[bold purple][⇒] 2 NUMARALI ODA AÇILDI: Manuel Telegram Token İmha[/bold purple]")
        token = input("Tenti RAT Bot Token girin: ").strip()
        if get_telegram_info(token):
            onay = input("\nSaldırganın bu bot üzerindeki veri bağı koparılsın mı? (E/H): ").strip().lower()
            if onay == 'e':
                nuke_telegram_bot(token)
                
    elif secim == "3":
        console.print("\n[bold yellow][⇒] 3 NUMARALI LABORATUVAR AÇILDI: Akıllı Kod Deşifresi[/bold yellow]")
        discords, telegrams = auto_extractor()
        
        if discords:
            console.print("\n[bold blue]Deşifre Edilen Discord Webhook'ları imha ediliyor...[/bold blue]")
            for d in discords:
                console.print(f"[cyan]Hedef Hat: {d[:50]}...[/cyan]")
                nuke_discord_webhook(d)
                
        if telegrams:
            console.print("\n[bold purple]Deşifre Edilen Telegram Token'ları kör ediliyor...[/bold purple]")
            for t in telegrams:
                console.print(f"[cyan]Hedef Bot: {t[:15]}...[/cyan]")
                nuke_telegram_bot(t)
                
        if not discords and not telegrams:
            console.print("[yellow][!] İnceleme tamamlandı: Metin içerisinde Tenti RAT izine rastlanmadı.[/yellow]")
            
    else:
        console.print("[bold red][-] Geçersiz numara! Lütfen sadece 1, 2 veya 3 yazın.[/bold red]")
