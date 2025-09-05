import requests
import time
from datetime import datetime
import os
import json

# A variável URLS_SITES agora depende APENAS do que for inserido
# na variável de ambiente 'URLS_SITES'.
URLS_SITES_VAR = os.getenv("URLS_SITES")
URLS_SITES = []

if URLS_SITES_VAR:
    try:
        URLS_SITES = json.loads(URLS_SITES_VAR)
        # Verifica se a lista de URLs não está vazia
        if not URLS_SITES:
            print("A variável de ambiente URLS_SITES está vazia. Nenhuma URL para monitorar.")
    except json.JSONDecodeError:
        print("Erro ao decodificar a variável de ambiente URLS_SITES. Verifique se o formato JSON está correto.")
        # Se houver erro, a lista permanece vazia
else:
    print("A variável de ambiente URLS_SITES não foi definida. Nenhuma URL para monitorar.")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TEMPOVERIFICA = int(os.getenv("TEMPOVERIFICA", "3600"))

def enviar_mensagem_discord(mensagem):
    # Só tenta enviar se o WEBHOOK_URL estiver definido
    if WEBHOOK_URL:
        payload = {
            "content": mensagem
        }
        try:
            requests.post(WEBHOOK_URL, json=payload)
        except requests.RequestException as e:
            print(f"[{datetime.now()}] Erro ao enviar para Discord: {e}")
    else:
        print("WEBHOOK_URL não está definido. Mensagem não enviada para o Discord.")

def verificar_site(url_site):
    try:
        resposta = requests.get(url_site, timeout=10)
        if resposta.status_code == 200:
            mensagem = f"✅ [{datetime.now().strftime('%d/%m %H:%M')}] O site {url_site} está ONLINE."
        else:
            mensagem = f"⚠️ [{datetime.now().strftime('%d/%m %H:%M')}] O site {url_site} respondeu com status {resposta.status_code}."
    except requests.RequestException:
        mensagem = f"❌ [{datetime.now().strftime('%d/%m %H:%M')}] O site {url_site} está FORA DO AR."

    print(mensagem)
    enviar_mensagem_discord(mensagem)

# Loop infinito
while True:
    # O loop só irá rodar se a lista de URLs não estiver vazia
    if URLS_SITES:
        for site in URLS_SITES:
            verificar_site(site)
    else:
        # Imprime uma mensagem e aguarda para verificar novamente se a variável foi alterada
        print("Nenhuma URL para monitorar. Aguardando o próximo ciclo.")

    time.sleep(TEMPOVERIFICA)