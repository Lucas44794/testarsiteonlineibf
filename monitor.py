import os
import requests
import json
import urllib3
import time
from datetime import datetime

# Desabilita o aviso sobre a verificação SSL desativada
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURAÇÕES ---
PORTAINER_URL = os.getenv("PORTAINER_URL")
USERNAME = os.getenv("PORTAINER_USERNAME")
PASSWORD = os.getenv("PORTAINER_PASSWORD")
ENDPOINT_ID = int(os.getenv("PORTAINER_ENDPOINT_ID", "1"))

# Monitoramento de sites e stacks
URLS_SITES_VAR = os.getenv("URLS_SITES")
URLS_SITES = []
if URLS_SITES_VAR:
    try:
        URLS_SITES = json.loads(URLS_SITES_VAR)
    except json.JSONDecodeError:
        print("Erro ao decodificar a variável de ambiente URLS_SITES. Verifique o formato JSON.")

STACK_NAMES_VAR = os.getenv("STACK_NAMES")
STACK_NAMES = []
if STACK_NAMES_VAR:
    try:
        STACK_NAMES = json.loads(STACK_NAMES_VAR)
    except json.JSONDecodeError:
        print("Erro ao decodificar a variável de ambiente STACK_NAMES. Verifique o formato JSON.")

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TEMPOVERIFICA = int(os.getenv("TEMPOVERIFICA", "3600"))

# Variável de controle para evitar reinícios múltiplos desnecessários
STACKS_RESTARTED = {name: False for name in STACK_NAMES}

def enviar_mensagem_discord(mensagem):
    """Envia uma mensagem para o webhook do Discord."""
    if not WEBHOOK_URL:
        print("WEBHOOK_URL não está definido. Mensagem não enviada para o Discord.")
        return

    payload = {"content": mensagem}
    try:
        requests.post(WEBHOOK_URL, json=payload, timeout=10)
    except requests.RequestException as e:
        print(f"[{datetime.now()}] Erro ao enviar para Discord: {e}")

def get_jwt_token():
    """Tenta autenticar no Portainer e retorna o token JWT."""
    if not USERNAME or not PASSWORD:
        print("Erro: Usuário ou senha do Portainer não definidos no arquivo .env.")
        return None

    auth_url = f"{PORTAINER_URL}/api/auth"
    auth_payload = {"username": USERNAME, "password": PASSWORD}

    try:
        print("Autenticando no Portainer...")
        response = requests.post(auth_url, json=auth_payload, verify=False, timeout=15)
        response.raise_for_status()
        jwt_token = response.json().get("jwt")
        if jwt_token:
            print("Autenticação bem-sucedida.")
            return jwt_token
        else:
            enviar_mensagem_discord("❌ Erro de autenticação no Portainer: Token JWT não encontrado.")
            print("Erro: Token JWT não encontrado na resposta.")
            return None
    except requests.exceptions.HTTPError as e:
        enviar_mensagem_discord(f"❌ Erro de autenticação HTTP no Portainer: {e}")
        print(f"Erro na autenticação! Código: {e.response.status_code}, Mensagem: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        enviar_mensagem_discord(f"❌ Ocorreu um erro de conexão com o Portainer: {e}")
        print(f"Ocorreu um erro de conexão: {e}")
        return None

def get_stack_id(jwt_token, stack_name):
    """Localiza e retorna o ID de uma stack pelo nome e endpoint ID."""
    stacks_url = f"{PORTAINER_URL}/api/stacks?endpointId={ENDPOINT_ID}"
    headers = {"Authorization": f"Bearer {jwt_token}"}

    try:
        response = requests.get(stacks_url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        stacks = response.json()
        for stack in stacks:
            if stack.get("Name") == stack_name and stack.get("EndpointId") == ENDPOINT_ID:
                return stack.get("Id")
        enviar_mensagem_discord(f"⚠️ Stack '{stack_name}' não encontrada no endpoint {ENDPOINT_ID}. Verifique o nome e o ID.")
        print(f"Stack '{stack_name}' não encontrada.")
        return None
    except requests.exceptions.RequestException as e:
        enviar_mensagem_discord(f"❌ Erro ao buscar stacks: {e}")
        print(f"Ocorreu um erro de conexão: {e}")
        return None

def get_stack_status(jwt_token, stack_id):
    """Obtém o status de uma stack."""
    stack_url = f"{PORTAINER_URL}/api/stacks/{stack_id}?endpointId={ENDPOINT_ID}"
    headers = {"Authorization": f"Bearer {jwt_token}"}
    try:
        response = requests.get(stack_url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        status = response.json().get('Status')
        return status
    except requests.exceptions.RequestException as e:
        print(f"Erro ao obter o status da stack: {e}")
        return None

def restart_stack(jwt_token, stack_id, stack_name):
    """Para e inicia a stack, verificando o estado atual."""
    headers = {"Authorization": f"Bearer {jwt_token}"}
    stack_status = get_stack_status(jwt_token, stack_id)

    if stack_status == 1:  # Status 1 significa que a stack está rodando
        # 1. Parar a stack
        stop_url = f"{PORTAINER_URL}/api/stacks/{stack_id}/stop?endpointId={ENDPOINT_ID}"
        enviar_mensagem_discord(f"⚙️ Tentando PARAR a stack '{stack_name}'...")
        try:
            response = requests.post(stop_url, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
            enviar_mensagem_discord(f"✅ Stack '{stack_name}' parada com sucesso.")
            print("Stack parada com sucesso.")
        except requests.exceptions.RequestException as e:
            enviar_mensagem_discord(f"❌ Erro ao parar a stack: {e}")
            print(f"Erro ao parar a stack: {e}")
            return False
    elif stack_status == 2:  # Status 2 significa que a stack está parada
        enviar_mensagem_discord(f"⚠️ Stack '{stack_name}' já estava parada. Prosseguindo com o início.")
        print("Stack já estava parada. Prosseguindo com o início.")
    else:
        enviar_mensagem_discord(f"❌ Não foi possível obter o status da stack '{stack_name}'.")
        print("Não foi possível obter o status da stack.")
        return False
        
    # 2. Aguardar
    print("Aguardando 10 segundos para iniciar novamente...")
    time.sleep(10)

    # 3. Iniciar a stack
    start_url = f"{PORTAINER_URL}/api/stacks/{stack_id}/start?endpointId={ENDPOINT_ID}"
    enviar_mensagem_discord(f"⚙️ Tentando INICIAR a stack '{stack_name}'...")
    try:
        response = requests.post(start_url, headers=headers, verify=False, timeout=30)
        response.raise_for_status()
        enviar_mensagem_discord(f"✅ Stack '{stack_name}' iniciada com sucesso.")
        print("Stack iniciada com sucesso.")
        return True
    except requests.exceptions.RequestException as e:
        enviar_mensagem_discord(f"❌ Erro ao iniciar a stack: {e}")
        print(f"Erro ao iniciar a stack: {e}")
        return False

def main_loop():
    """Loop principal que monitora os sites e reinicia a stack se necessário."""
    if len(URLS_SITES) != len(STACK_NAMES):
        enviar_mensagem_discord("Erro: O número de URLs e nomes de stacks não corresponde. Verifique suas variáveis de ambiente.")
        print("Erro: O número de URLs e nomes de stacks não corresponde.")
        return

    if not URLS_SITES:
        enviar_mensagem_discord("Nenhuma URL para monitorar. O script está em espera.")
        print("Nenhuma URL para monitorar.")
        time.sleep(TEMPOVERIFICA)
        return

    for i, site in enumerate(URLS_SITES):
        stack_name = STACK_NAMES[i]
        try:
            resposta = requests.get(site, timeout=15)
            if resposta.status_code == 200:
                # O site está OK, envia a mensagem e reseta o flag de reinício
                enviar_mensagem_discord(f"✅ [{datetime.now().strftime('%d/%m %H:%M')}] O site {site} está ONLINE.")
                print(f"✅ Site {site} está ONLINE.")
                STACKS_RESTARTED[stack_name] = False
            else:
                print(f"⚠️ O site {site} respondeu com status {resposta.status_code}.")
                # Se o site não estiver OK e a stack ainda não foi reiniciada neste ciclo
                if not STACKS_RESTARTED.get(stack_name, False):
                    enviar_mensagem_discord(f"⚙️ O site {site} respondeu com status {resposta.status_code}. Tentando reiniciar a stack '{stack_name}'.")
                    
                    jwt_token = get_jwt_token()
                    if jwt_token:
                        stack_id = get_stack_id(jwt_token, stack_name)
                        if stack_id:
                            if restart_stack(jwt_token, stack_id, stack_name):
                                STACKS_RESTARTED[stack_name] = True
                    time.sleep(10)
        except requests.RequestException:
            print(f"❌ O site {site} está FORA DO AR.")
            # Se o site está offline e a stack ainda não foi reiniciada neste ciclo
            if not STACKS_RESTARTED.get(stack_name, False):
                enviar_mensagem_discord(f"❌ O site {site} está FORA DO AR. Tentando reiniciar a stack '{stack_name}'.")
                
                jwt_token = get_jwt_token()
                if jwt_token:
                    stack_id = get_stack_id(jwt_token, stack_name)
                    if stack_id:
                        if restart_stack(jwt_token, stack_id, stack_name):
                            STACKS_RESTARTED[stack_name] = True
                time.sleep(10)

# --- EXECUÇÃO ---
if __name__ == "__main__":
    while True:
        main_loop()
        print(f"\n--- Próxima verificação em {TEMPOVERIFICA} segundos. ---\n")
        time.sleep(TEMPOVERIFICA)
        # Reseta o flag para o próximo ciclo de verificação
        STACKS_RESTARTED = {name: False for name in STACK_NAMES}