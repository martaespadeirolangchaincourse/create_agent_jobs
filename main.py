import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from google import genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Erro: GOOGLE_API_KEY não encontrada!")

client = genai.Client(api_key=api_key)

EMPRESAS_TARGET = {
    "Netflix": "https://explore.jobs.netflix.net/careers?query=Data",
    "Uber": "https://www.uber.com/pt/pt/careers/teams/data-science/",
    "Spotify": "https://www.lifeatspotify.com/jobs?q=Data",
    "Airbnb": "https://careers.airbnb.com/positions/",
    "Booking": "https://careers.booking.com/search-results/?q=Data",
    "Google": "https://www.google.com/about/careers/applications/jobs/results?q=Data",
    "Amazon": "https://www.amazon.jobs/en/search?base_query=data+scientist",
    "Critical TechWorks": "https://join.criticaltechworks.com/jobs",
    "Glovo": "https://jobs.glovoapp.com/departments/data/",
    "Mercedes-Benz.io": "https://www.mercedes-benz.io/jobs",
    "VW Digital Solutions": "https://jobs.volkswagen-group.com/VWGDS/?locale=en_US"
}


# --- FUNÇÕES DE APOIO ---

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


def agente_decide_vaga(titulo, descricao):
    prompt = f"Analisa a vaga: {titulo}. Descrição: {descricao[:2000]}. Responde SIM se for Data Analyst/Scientist em DESPORTO ou Junior Data Engineer. Caso contrário, responde NAO. Responde apenas SIM ou NAO."
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return "SIM" in response.text.strip().upper()
    except:
        return False


def enviar_email(vagas):
    meu_email = os.getenv("EMAIL_USER")
    minha_senha = os.getenv("EMAIL_PASS")
    if not vagas or not meu_email: return

    corpo = "<h2>🚀 Novas Vagas Encontradas</h2><ul>"
    for v in vagas:
        corpo += f"<li><strong>{v['titulo']}</strong> - <a href='{v['link']}'>Link</a></li>"
    corpo += "</ul>"

    msg = MIMEMultipart()
    msg['Subject'] = f"🎯 {len(vagas)} Novas Vagas Tech/Sports"
    msg['From'] = meu_email
    msg['To'] = meu_email
    msg.attach(MIMEText(corpo, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(meu_email, minha_senha)
        server.send_message(msg)
        server.quit()
        print("✉️ E-mail enviado!")
    except Exception as e:
        print(f"Erro e-mail: {e}")


# --- FUNÇÕES DE SCRAPING ---

def configurar_driver():
    is_github = os.getenv("GITHUB_ACTIONS") == "true"
    if is_github:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=chrome_options)
    else:
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        return uc.Chrome(version_main=145, options=options)


def procurar_linkedin(driver):
    vagas_aprovadas = []
    url = "https://www.linkedin.com/jobs/search/?keywords=Data%20Analyst%20Sports&location=Lisbon&f_WT=1%2C2"
    print("--- ETAPA 1: LinkedIn ---")
    driver.get(url)
    time.sleep(6)
    cards = driver.find_elements(By.CLASS_NAME, "base-card")

    for card in cards[:10]:
        try:
            titulo = card.find_element(By.CLASS_NAME, "base-search-card__title").text
            link = card.find_element(By.TAG_NAME, "a").get_attribute("href")
            if not gerir_memoria_vagas(link):
                # Vai ao detalhe da vaga
                driver.get(link)
                time.sleep(3)
                desc = driver.find_element(By.TAG_NAME, "body").text
                if agente_decide_vaga(titulo, desc):
                    vagas_aprovadas.append({"titulo": f"[LinkedIn] {titulo}", "link": link})
        except:
            continue
    return vagas_aprovadas


def verificar_sites_diretos(driver):
    vagas_encontradas = []
    print("\n--- ETAPA 2: Sites Oficiais ---")
    for empresa, url in EMPRESAS_TARGET.items():
        try:
            print(f"🌐 {empresa}...")
            driver.get(url)
            time.sleep(5)
            texto = driver.find_element(By.TAG_NAME, "body").text
            prompt = f"Analisa o texto de carreiras da {empresa}. Se houver vagas de Data Analyst ou Data Engineer, lista-as no formato: Titulo | Link. Se não houver, responde NADA. Texto: {texto[:4000]}"
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            res = response.text.strip()
            if "NADA" not in res.upper():
                for linha in res.split('\n'):
                    if "|" in linha:
                        t, l = linha.split("|")
                        if not gerir_memoria_vagas(l.strip()):
                            vagas_encontradas.append({"titulo": f"[{empresa}] {t.strip()}", "link": l.strip()})
        except:
            continue
    return vagas_encontradas


# --- EXECUÇÃO ---

if __name__ == "__main__":
    browser = configurar_driver()

    # Executa as duas fontes
    lista_linkedin = procurar_linkedin(browser)
    lista_direta = verificar_sites_diretos(browser)

    total_vagas = lista_linkedin + lista_direta

    browser.quit()

    print(f"\nTotal de novas vagas: {len(total_vagas)}")
    if total_vagas:
        enviar_email(total_vagas)
    else:
        print("Nada de novo hoje.")