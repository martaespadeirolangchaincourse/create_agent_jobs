import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import google.generativeai as genai
import time
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente (API Key)
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("Erro: GOOGLE_API_KEY não encontrada! Verifica os Secrets ou o .env")


# 1. CONFIGURAÇÃO DA IA
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')


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
        response = model.generate_content(prompt)
        return "SIM" in response.text.strip().upper()
    except Exception as e:
        print(f"Erro na IA: {e}")
        return False


def gerir_memoria_vagas(link):
    """Verifica se o link já foi processado antes para não repetir."""
    ficheiro = "vagas_vistas.txt"
    if not os.path.exists(ficheiro):
        with open(ficheiro, "w") as f: pass

    with open(ficheiro, "r") as f:
        vistas = f.read().splitlines()

    if link in vistas:
        return True  # Já viu

    with open(ficheiro, "a") as f:
        f.write(link + "\n")
    return False  # É nova


def iniciar_agente_vagas():
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Necessário para o GitHub
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    #driver=uc.Chrome(options=options)
    #driver = uc.Chrome(version_main=145)
    if os.getenv("GITHUB_ACTIONS") == "true":
        print("Ambiente GitHub detectado. A usar versão automática do Chrome.")
        driver = uc.Chrome(options=options)
    else:
        # Se estiver no teu PC (Windows/Mac), usa a versão 145 que instalaste
        print("Ambiente Local detectado. A usar Chrome v145.")
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

            # MEMÓRIA: Só avança se o link for novo
            if not gerir_memoria_vagas(link):
                vagas_para_analisar.append({"titulo": titulo, "link": link})
            else:
                print(f"⏭️ Ignorada (já analisada anteriormente): {titulo}")
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


if __name__ == "__main__":
    vagas_finais = iniciar_agente_vagas()

    print("\n" + "=" * 30 + "\nRELATÓRIO FINAL\n" + "=" * 30)
    if not vagas_finais:
        print("Nenhuma vaga nova e relevante hoje.")
    else:
        for v in vagas_finais:
            print(f"🎯 {v['titulo']}\n🔗 {v['link']}\n")

    # Aqui podes chamar a tua função de e-mail no final