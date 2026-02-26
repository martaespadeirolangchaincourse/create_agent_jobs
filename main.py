import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from google import genai  # Usando apenas a biblioteca nova

##--- libraries to send e-mail
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# Carregar variáveis de ambiente
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Erro: GOOGLE_API_KEY não encontrada!")

# 1. CONFIGURAÇÃO DA IA (Nova API do Google)
client = genai.Client(api_key=api_key)

def agente_decide_vaga(titulo, descricao):
    prompt = f"""
    És um assistente de carreira. Analisa a vaga abaixo:
    Título: {titulo}
    Descrição: {descricao[:2000]} 

    Critérios de aprovação (Responde 'SIM' se cumprir UM deles):
    1. A vaga é para Data Analyst ou Data Scientist especificamente no setor do DESPORTO (futebol, clubes, performance).
    2. A vaga é para Junior Data Engineer (pode ser em qualquer área).

    Se for uma vaga de Data Analyst que NÃO seja de desporto, responde 'NAO'.
    Responde apenas com a palavra 'SIM' ou 'NAO'.
    """
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return "SIM" in response.text.strip().upper()
    except Exception as e:
        print(f"Erro na IA: {e}")
        return False

def gerir_memoria_vagas(link):
    ficheiro = "vagas_vistas.txt"
    if not os.path.exists(ficheiro):
        with open(ficheiro, "w") as f: pass

    with open(ficheiro, "r") as f:
        vistas = f.read().splitlines()

    if link in vistas:
        return True

    with open(ficheiro, "a") as f:
        f.write(link + "\n")
    return False

def iniciar_agente_vagas():
    # Detectar ambiente
    is_github = os.getenv("GITHUB_ACTIONS") == "true"

    if is_github:
        print("Ambiente GitHub detectado. Usando Selenium Standard.")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=chrome_options)
    else:
        print("Ambiente Local detectado. Usando undetected-chromedriver v145.")
        options = uc.ChromeOptions()
        # No teu PC, podes querer ver o browser a abrir (comenta o headless se quiseres)
        options.add_argument("--headless")
        driver = uc.Chrome(version_main=145, options=options)

    url_pesquisa = "https://www.linkedin.com/jobs/search/?keywords=Data%20Analyst%20Sports&location=Lisbon&f_WT=1%2C2"

    print("--- ETAPA 1: Recolhendo links ---")
    driver.get(url_pesquisa)
    time.sleep(6)

    cards = driver.find_elements(By.CLASS_NAME, "base-card")
    vagas_para_analisar = []

    for card in cards[:10]:
        try:
            titulo = card.find_element(By.CLASS_NAME, "base-search-card__title").text
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")

            if not gerir_memoria_vagas(link):
                vagas_para_analisar.append({"titulo": titulo, "link": link})
            else:
                print(f"⏭️ Ignorada (repetida): {titulo}")
        except:
            continue

    vagas_aprovadas = []
    print(f"\n--- ETAPA 2: Análise IA de {len(vagas_para_analisar)} novas vagas ---")

    for vaga in vagas_para_analisar:
        print(f"🧐 Analisando: {vaga['titulo']}...")
        driver.get(vaga['link'])
        time.sleep(4)
        try:
            corpo_texto = driver.find_element(By.TAG_NAME, "body").text
            if agente_decide_vaga(vaga['titulo'], corpo_texto):
                print(f"✅ APROVADA")
                vagas_aprovadas.append(vaga)
            else:
                print(f"❌ REJEITADA")
        except Exception as e:
            print(f"Erro: {e}")

    driver.quit()
    return vagas_aprovadas


def enviar_email(vagas):
    meu_email = os.getenv("EMAIL_USER")
    minha_senha = os.getenv("EMAIL_PASS")
    destinatario = meu_email

    if not vagas:
        print("Sem vagas novas para enviar.")
        return

    corpo_html = "<h2>🚀 Novas Vagas de Data & Sports Encontradas</h2>"
    corpo_html += "<p>O teu agente analisou o LinkedIn e selecionou estas oportunidades:</p><ul>"

    for v in vagas:
        corpo_html += f"<li><strong>{v['titulo']}</strong><br><a href='{v['link']}'>Ver no LinkedIn</a></li><br>"

    corpo_html += "</ul><p>Boa sorte!</p>"

    msg = MIMEMultipart()
    msg['From'] = meu_email
    msg['To'] = destinatario
    msg['Subject'] = f"🎯 {len(vagas)} Novas Vagas (Data Analyst/Engineer)"
    msg.attach(MIMEText(corpo_html, 'html'))

    try:

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()  # Segurança
        server.login(meu_email, minha_senha)
        server.send_message(msg)
        server.quit()
        print("✉️ E-mail enviado com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao enviar e-mail: {e}")


if __name__ == "__main__":
    vagas_finais = iniciar_agente_vagas()

    print("\n" + "=" * 30 + "\nRELATÓRIO FINAL\n" + "=" * 30)

    if not vagas_finais:
        print("Nenhuma vaga nova e relevante hoje.")
    else:
        for v in vagas_finais:
            print(f"🎯 {v['titulo']}\n🔗 {v['link']}\n")

        # 2. Enviar por e-mail
        enviar_email(vagas_finais)