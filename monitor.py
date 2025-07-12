import requests
import time
from datetime import datetime
import os

URL_SITE = os.getenv("URL_SITE", "https://ibfescola.com.br")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TEMPOVERIFICA = os.getenv("TEMPOVERIFICA")

def enviar_mensagem_discord(mensagem):
    payload = {
        "content": mensagem
    }
    try:
        requests.post(WEBHOOK_URL, json=payload)
    except requests.RequestException as e:
        print(f"[{datetime.now()}] Erro ao enviar para Discord: {e}")

def verificar_site():
    try:
        resposta = requests.get(URL_SITE, timeout=10)
        if resposta.status_code == 200:
            mensagem = f"✅ [{datetime.now().strftime('%d/%m %H:%M')}] O site {URL_SITE} está ONLINE."
        else:
            mensagem = f"⚠️ [{datetime.now().strftime('%d/%m %H:%M')}] O site respondeu com status {resposta.status_code}."
    except requests.RequestException:
        mensagem = f"❌ [{datetime.now().strftime('%d/%m %H:%M')}] O site {URL_SITE} está FORA DO AR."

    print(mensagem)
    enviar_mensagem_discord(mensagem)

# Loop infinito: verifica a cada 1 hora
while True:
    verificar_site()
    time.sleep(TEMPOVERIFICA)