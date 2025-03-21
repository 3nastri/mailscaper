# -*- coding: utf-8 -*-
"""Scraper.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1P7ojJn2lHnhscEohQAJ1ZHM0-E9-JTMQ
"""

import requests

# Conferma che il notebook è stato avviato dal Webhook
requests.get("https://hook.eu2.make.com/cmy5e6w3im83yag7sl5qphxhqwyiahxu")

print("✅ Notebook avviato automaticamente!")

!mkdir -p /content/drive/MyDrive/Colab/cache

from google.colab import drive
drive.mount('/content/drive')

!pip install transformers torch --quiet

# -*- coding: utf-8 -*-
"""mailscaper.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1K6UNpC2bBP2xdwguOvGZ6k144sOKO_i2
"""

import os
import sys

os.environ["HF_HOME"] = "/content/drive/MyDrive/Colab/cache"

# Verifica la versione di NumPy
import numpy
print(f"✅ NumPy versione in uso: {numpy.__version__}")

import imaplib
import email
from email.header import decode_header
from transformers import pipeline
import smtplib
from email.mime.text import MIMEText


# Configurazione
EMAIL_USER = "officinasociale24@gmail.com"
EMAIL_PASS = "gwwqfdebhhdggpwt"
IMAP_SERVER = "imap.gmail.com"
LABEL = "Google Alerts"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
DESTINATARI = ["officinasociale24@gmail.com", "wal.celletti@gmail.com"]

# Connessione alla casella di posta
def connect_email():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_USER, EMAIL_PASS)
    return mail

# Funzione per ottenere tutte le email dalla cartella "Google Alerts"
import datetime

def fetch_emails():
    mail = connect_email()
    mail.select('"Google Alert"')

    # Calcolo della data di ieri (24 ore fa)
    ieri = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")

    # Ricerca solo email arrivate dopo la data di ieri
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

# Modello open-source per analisi del testo (usiamo un modello BART per la classificazione)
classifier = pipeline("zero-shot-classification", model="valhalla/distilbart-mnli-12-3")

# Categorie personalizzate per il filtraggio
target_categories = [
    "Bandi di gara", "Avvisi pubblici", "Finanziamenti", "Contributi pubblici"
]

def filter_relevant_emails(emails):
    relevant_emails = []
    for subject, _ in emails:  # Ignoriamo il corpo dell'email
        result = classifier(subject, candidate_labels=target_categories)
        best_label = result["labels"][0]
        best_score = result["scores"][0]
        if best_score > 0.7:
            relevant_emails.append((subject, "Corpo ignorato", best_label))

    return relevant_emails

# Funzione per inviare email con il riepilogo
def send_summary(filtered_emails):
    if not filtered_emails:
        return  # Se non ci sono email da segnalare, non invia nulla

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

# Lettura email
emails = fetch_emails()
print(f"📩 Email totali trovate: {len(emails)}")

# Debug per verificare se ci sono email
if len(emails) > 0:
    print("📌 Esempio di una email scaricata:")
    print(f"Soggetto: {emails[0][0]}")
    print(f"Corpo: {emails[0][1][:500]}...")  # Stampiamo solo i primi 500 caratteri

# Filtraggio email
print("🔎 Inizio filtraggio email...")

filtered_emails = []
for i, (subject, body) in enumerate(emails):
    print(f"📨 Analizzando email {i+1}/{len(emails)}: {subject[:50]}...")
    try:
        short_body = body[:500]  # Prendiamo solo i primi 500 caratteri
        result = classifier(short_body, candidate_labels=target_categories)
        best_label = result["labels"][0]
        best_score = result["scores"][0]
        if best_score > 0.7:
            filtered_emails.append((subject, body, best_label))
    except Exception as e:
        print(f"❌ Errore nell'analisi dell'email {i+1}: {e}")

print(f"🎯 Email filtrate come utili: {len(filtered_emails)}")

# Debug per vedere le email filtrate
for email_data in filtered_emails:
    print(f"✅ Email utile trovata: {email_data[0]} | Categoria: {email_data[2]}")

# Invia riepilogo solo se ci sono email utili
if len(filtered_emails) > 0:
    send_summary(filtered_emails)
    print("📧 Riepilogo inviato con successo!")
else:
    print("⚠️ Nessuna email utile trovata.")

print("✅ Script completato!")