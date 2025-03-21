import requests
import os
import sys
import numpy
import imaplib
import email
import datetime
from email.header import decode_header
from transformers import pipeline
import smtplib
from email.mime.text import MIMEText

try:
    print("✅ Notebook avviato automaticamente!")

    # Imposta la directory per la cache (GitHub Actions)
    os.makedirs("./cache", exist_ok=True)
    os.environ["HF_HOME"] = "./cache"

    print(f"✅ NumPy versione in uso: {numpy.__version__}")

    # Configurazione email
    EMAIL_USER = "officinasociale24@gmail.com"
    EMAIL_PASS = "gwwqfdebhhdggpwt"
    IMAP_SERVER = "imap.gmail.com"
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    DESTINATARI = ["officinasociale24@gmail.com", "wal.celletti@gmail.com"]

    def connect_email():
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_USER, EMAIL_PASS)
        return mail

    def fetch_emails():
        mail = connect_email()
        mail.select('"Google Alert"')

        ieri = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{ieri}")')
        email_ids = messages[0].split()

        emails = []
        for e_id in email_ids:
            _, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    subject = subject.decode(encoding or "utf-8") if isinstance(subject, bytes) else subject
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    emails.append((subject, body))
        mail.logout()
        return emails

    # Modello AI per analisi del testo
    classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-3")
    target_categories = ["Bandi di gara", "Avvisi pubblici", "Finanziamenti", "Contributi pubblici"]

    def filter_relevant_emails(emails):
        relevant_emails = []
        for subject, _ in emails:
            result = classifier(subject, candidate_labels=target_categories)
            best_label = result["labels"][0]
            best_score = result["scores"][0]
            if best_score > 0.7:
                relevant_emails.append((subject, "Corpo ignorato", best_label))
        return relevant_emails

    def send_summary(filtered_emails):
        if not filtered_emails:
            return

        summary_content = "\n\n".join(
            [f"**{email_data[0]}**\nCategoria: {email_data[2]}\n{email_data[1][:500]}..." for email_data in filtered_emails]
        )

        msg = MIMEText(f"Ecco le email filtrate del giorno:\n\n{summary_content}", "plain", "utf-8")
        msg["Subject"] = "Riepilogo Bandi e Avvisi Pubblici"
        msg["From"] = EMAIL_USER
        msg["To"] = ", ".join(DESTINATARI)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, DESTINATARI, msg.as_string())
        server.quit()

    print("✅ Avvio script...")

    emails = fetch_emails()
    print(f"📩 Email totali trovate: {len(emails)}")

    if len(emails) > 0:
        print("📌 Esempio di una email scaricata:")
        print(f"Soggetto: {emails[0][0]}")
        print(f"Corpo: {emails[0][1][:500]}...")

    print("🔎 Inizio filtraggio email...")

    filtered_emails = []
    for i, (subject, body) in enumerate(emails):
        print(f"📨 Analizzando email {i+1}/{len(emails)}: {subject[:50]}...")
        try:
            short_body = body[:500]
            result = classifier(short_body, candidate_labels=target_categories)
            best_label = result["labels"][0]
            best_score = result["scores"][0]
            if best_score > 0.7:
                filtered_emails.append((subject, body, best_label))
        except Exception as e:
            print(f"❌ Errore nell'analisi dell'email {i+1}: {e}")

    print(f"🎯 Email filtrate come utili: {len(filtered_emails)}")

    for email_data in filtered_emails:
        print(f"✅ Email utile trovata: {email_data[0]} | Categoria: {email_data[2]}")

    if len(filtered_emails) > 0:
        send_summary(filtered_emails)
        print("📧 Riepilogo inviato con successo!")
    else:
        print("⚠️ Nessuna email utile trovata.")

    # Notifica il completamento a Make.com
    requests.get("https://hook.eu2.make.com/cmy5e6w3im83yag7sl5qphxhqwyiahxu")
    print("✅ Script completato!")

except Exception as e:
    print(f"❌ ERRORE GENERALE: {e}")
