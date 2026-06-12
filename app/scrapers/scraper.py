import asyncio
import json
import time
import sys
import re  # Novo import para extrair o tempo do erro por Regex
from pathlib import Path
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types

# --- HACK DE PATH DINÂMICO ---
raiz_projeto = str(Path(__file__).resolve().parent.parent.parent)
if raiz_projeto not in sys.path:
    sys.path.insert(0, raiz_projeto)

from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

class Plano(BaseModel):
    plano: str = Field(description="Nome do plano. Ex: Padrão com Anúncios, Premium, Mega Fan, Familiar")
    valor: str = Field(description="O valor do plano formatado contendo a moeda. Ex: R$ 24,90")
    ciclo: str = Field(description="Ciclo de faturamento. Deve ser estritamente: 'Mensal', 'Anual (À vista)', 'Anual (Fracionado mensal)' ou 'Taxa / Adicional'")
    observacoes: Optional[str] = Field(description="Detalhes extras importantes, como 'Apenas para estudantes' ou 'Adicional de tela extra'")

class ListaPlanos(BaseModel):
    streaming: str = Field(description="Nome do serviço de streaming")
    planos: List[Plano]

def processar_texto_com_ia(nome_streaming, texto_bruto):
    tentativas_maximas = 3
    delay = 2

    prompt = f"""
    Você é um extrator de dados especialista em assinaturas de streaming.
    Analise o texto bruto extraído do site do {nome_streaming} e descubra todos os planos disponíveis, seus respectivos preços e condições de faturamento.
    ignore propagandas ou textos que não sejam relacionados a valores de planos antigos ou atuais praticados no Brasil.
    
    Texto bruto do site:
    \"\"\"{texto_bruto}\"\"\"
    """

    for tentativa in range(1, tentativas_maximas + 1):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ListaPlanos,
                    temperature=0.1
                ),
            )
            return response.text
        except Exception as e:
            erro_str = str(e)
            if "503" in erro_str or "UNAVAILABLE" in erro_str or "high demand" in erro_str:
                if tentativa < tentativas_maximas:
                    print(f"⚠️ [GEMINI AI] Servidor instável (503). Tentativa {tentativa}/{tentativas_maximas} falhou. Aguardando {delay}s antes de reprocessar...")
                    time.sleep(delay)
                    delay *= 2
                    continue
            return f'{{"streaming": "{nome_streaming}", "planos": [], "error": "{erro_str}"}}'

async def tratar_interacoes_especificas(page, nome_streaming):
    try:
        if nome_streaming == "Crunchyroll":
            botao_anual = page.get_by_text("Anual", exact=True)
            if await botao_anual.is_visible():
                await botao_anual.click()
                await page.wait_for_timeout(1500)
        elif nome_streaming == "YouTube Premium":
            botao_mais = page.get_by_text("Mais options", exact=False)
            if await botao_mais.is_visible():
                await botao_mais.click()
                await page.wait_for_timeout(1000)
    except Exception:
        pass

async def tentar_acessar_pagina(browser, url, nome_streaming):
    print(f"\n🌐 [PLAYWRIGHT] Raspando texto bruto do {nome_streaming}...")
    context = await browser.new_context(user_agent=settings.USER_AGENT)
    page = await context.new_page()
    texto_acumulado = ""
    
    try:
        await page.goto(url, wait_until="networkidle", timeout=25000)
        await page.wait_for_timeout(3000)
        
        texto_acumulado += await page.locator("body").inner_text()
        await tratar_interacoes_especificas(page, nome_streaming)
        texto_acumulado += "\n" + await page.locator("body").inner_text()
        
        await context.close()
        
        print(f"🧠 [GEMINI AI] Processando e estruturando dados do {nome_streaming}...")
        json_estruturado = processar_texto_com_ia(nome_streaming, texto_acumulado)
        return json_estruturado
        
    except Exception as e:
        await context.close()
        return f'{{"streaming": "{nome_streaming}", "planos": [], "error": "{str(e)}"}}'

async def rodar_scrapers():
    print("🚀 Inicializando motor híbrido (Playwright + Gemini API)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        for stream in settings.STREAMINGS:
            json_resultado = await tentar_acessar_pagina(browser, stream["url"], stream["nome"])
            
            # --- CONDICIONAL DE BLOQUEIO POR ESTOURO DE COTA (429) ---
            if "RESOURCE_EXHAUSTED" in json_resultado or "429" in json_resultado:
                await browser.close()
                print(f"\n🛑 [CRÍTICO] Cota estourada no {stream['nome']}. Interrompendo a execução geral!")
                
                # Procura o tempo sugerido no erro (ex: "Please retry in 21.775904231s." ou "retryDelay: '21s'")
                tempo_espera = "alguns minutos (verifique o painel do Google Cloud)"
                match = re.search(r"Please retry in ([^']+?s)\.", json_resultado)
                if match:
                    tempo_espera = match.group(1)
                else:
                    match_alt = re.search(r"retryDelay': '(\d+s)'", json_resultado)
                    if match_alt:
                        tempo_espera = match_alt.group(1)
                
                print(f"⏳ Tempo estimado para poder rodar de novo: {tempo_espera}\n")
                sys.exit(1) # Finaliza o script imediatamente com código de erro
            
            print(f"\n--- 📊 {stream['nome'].upper()} JSON FINAL ---")
            print(json_resultado)
            print("-" * 60 + "\n")
            
        await browser.close()
        print("🔒 Processo finalizado com sucesso.")

if __name__ == "__main__":
    asyncio.run(rodar_scrapers())