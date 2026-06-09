import asyncio
import os
from playwright.async_api import async_playwright
from pydantic import BaseModel, Field
from typing import List, Optional
from google import genai
from google.genai import types

GEMINI_API_KEY = "AQ.Ab8RN6K-c9d4pJgpvoibLtt2Hbroa21ev-mb_HFv26BLyg8RfQ"
client = genai.Client(api_key=GEMINI_API_KEY)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class Plano(BaseModel):
    plano: str = Field(description="Nome do plano. Ex: Padrão com Anúncios, Premium, Mega Fan, Familiar")
    valor: str = Field(description="O valor do plano formatado contendo a moeda. Ex: R$ 24,90")
    ciclo: str = Field(description="Ciclo de faturamento. Deve ser estritamente: 'Mensal', 'Anual (À vista)', 'Anual (Fracionado mensal)' ou 'Taxa / Adicional'")
    observacoes: Optional[str] = Field(description="Detalhes extras importantes, como 'Apenas para estudantes' ou 'Adicional de tela extra'")

class ListaPlanos(BaseModel):
    streaming: str = Field(description="Nome do serviço de streaming")
    planos: List[Plano]

def processar_texto_com_ia(nome_streaming, texto_bruto):
    try:
        prompt = f"""
        Você é um extrator de dados especialista em assinaturas de streaming.
        Analise o texto bruto extraído do site do {nome_streaming} e descubra todos os planos disponíveis, seus respectivos preços e condições de faturamento.
        ignore propagandas ou textos que não sejam relacionados a valores de planos atuais praticados no Brasil.
        
        Texto bruto do site:
        \"\"\"{texto_bruto}\"\"\"
        """
        
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
        return f'{{"streaming": "{nome_streaming}", "planos": [], "error": "{str(e)}"}}'

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
    print(f"🌐 [PLAYWRIGHT] Raspando texto bruto do {nome_streaming}...")
    context = await browser.new_context(user_agent=USER_AGENT)
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
    streamings = [
        {"nome": "Netflix", "url": "https://help.netflix.com/pt/node/24926"},
        {"nome": "Spotify", "url": "https://www.spotify.com/br-pt/premium/#plans"},
        {"nome": "Crunchyroll", "url": "https://www.crunchyroll.com/pt-br/welcome"},
        {"nome": "Prime Video", "url": "https://www.primevideo.com/signup/ref=atv_nb_join_prime"},
        {"nome": "HBO Max", "url": "https://www.hbomax.com/br/pt"},
        {"nome": "Disney+", "url": "https://www.disneyplus.com/pt-br"},
        {"nome": "Apple TV", "url": "https://tv.apple.com/br"},
        {"nome": "YouTube Premium", "url": "https://www.youtube.com/premium?ybp=Sg0IBhIJdW5saW1pdGVk4AEB"}
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        
        for stream in streamings:
            json_resultado = await tentar_acessar_pagina(browser, stream["url"], stream["nome"])
            print(f"\n--- 📊 {stream['nome'].upper()} JSON FINAL ---")
            print(json_resultado)
            print("-" * 60 + "\n")
            
        await browser.close()
        print("🔒 Processo finalizado.")

if __name__ == "__main__":
    asyncio.run(rodar_scrapers())