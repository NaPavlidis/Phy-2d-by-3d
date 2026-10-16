import os
import textwrap

def mapear_catalogo(caminho_catalogo):
    """
    Mapeia a estrutura de pastas do Catálogo e retorna o status dos modelos que possuem arquivos .svg.
    Estrutura esperada:
    CATALOGO / [MODALIDADE] / [MODELO_CODIGO] / SVG / *.svg
    """
    if not os.path.exists(caminho_catalogo):
        print(f"❌ Erro: O diretório do catálogo '{caminho_catalogo}' não foi encontrado.")
        return

    # Dicionário para armazenar o resultado por modalidade
    # Ex: { 'KART': {'svg_count': 8, 'pastas_prontas': ['KAR25001', 'KAR25002', ...]} }
    modalidades = {}

    # Lista de modalidades encontradas no diretório raiz do Catálogo
    try:
        itens_raiz = sorted(os.listdir(caminho_catalogo))
    except Exception as e:
        print(f"❌ Erro ao acessar o diretório: {e}")
        return

    for item in itens_raiz:
        caminho_modalidade = os.path.join(caminho_catalogo, item)
        
        # Considera apenas diretórios como modalidades
        if os.path.isdir(caminho_modalidade):
            nome_modalidade = item.upper()
            
            pastas_prontas = []
            svg_count_total = 0

            # Varre as pastas de modelos/códigos dentro da modalidade
            try:
                modelos = sorted(os.listdir(caminho_modalidade))
                for modelo_cod in modelos:
                    caminho_modelo = os.path.join(caminho_modalidade, modelo_cod)
                    
                    if os.path.isdir(caminho_modelo):
                        # Verifica se existe a subpasta "SVG" (ou variações de case como "svg")
                        caminho_svg_dir = None
                        for sub in os.listdir(caminho_modelo):
                            if sub.upper() == "SVG" and os.path.isdir(os.path.join(caminho_modelo, sub)):
                                caminho_svg_dir = os.path.join(caminho_modelo, sub)
                                break
                        
                        # Se a pasta SVG existe, conta os arquivos .svg contidos nela
                        if caminho_svg_dir:
                            svgs = [f for f in os.listdir(caminho_svg_dir) if f.lower().endswith('.svg')]
                            qtd_svgs = len(svgs)
                            if qtd_svgs > 0:
                                svg_count_total += qtd_svgs
                                pastas_prontas.append(modelo_cod)
            except Exception as e:
                print(f"⚠️ Erro ao ler a modalidade {nome_modalidade}: {e}")

            modalidades[nome_modalidade] = {
                'svg_count': svg_count_total,
                'pastas_prontas': pastas_prontas
            }

    # ==============================================================================
    # EXIBIÇÃO FORMATADA DO RELATÓRIO
    # ==============================================================================
    totais_por_modalidade = {}
    total_geral_trofeus = 0

    for mod, dados in modalidades.items():
        svg_count = dados['svg_count']
        pastas = dados['pastas_prontas']
        pronto = svg_count > 0

        status_str = "✓ Pronto" if pronto else "✗ Não pronto"
        
        if pronto:
            pastas_str = ", ".join(pastas)
            totais_por_modalidade[mod] = len(pastas)
            total_geral_trofeus += len(pastas)
        else:
            pastas_str = "—"

        # Formata a linha de pastas prontas com quebra automática elegante se for longa
        pastas_formatadas = textwrap.fill(
            f"Pastas Prontas: {pastas_str}",
            width=80,
            subsequent_indent="   "
        )

        print(f"Modalidade: {mod}")
        print(f"Status: {status_str}")
        print(f"SVG Count: {svg_count}")
        print(f"{pastas_formatadas}")
        print("────────────────────────────────────────")

    # Seção de Totais
    print("📈 Totais")
    print(f"- Total pronto para catalogar: {total_geral_trofeus} troféus")
    for mod, qtd in totais_por_modalidade.items():
        print(f"- {mod}: {qtd}")

    # Seção de Observações
    print("\n📝 Observações")
    print("- O critério de \"pronto\" é a presença de pelo menos um arquivo .svg em alguma subpasta")

    # Seção do Caminho do Catálogo
    print("\n📁 Caminho do Catálogo (Predefinido)")
    print(f"Diretório raiz do catálogo: {caminho_catalogo}")
    print("Este caminho é constante e não precisa ser procurado — está predefinido para evitar buscas repetidas.\n")


# ==============================================================================
# EXECUÇÃO DO SCRIPT
# ==============================================================================
if __name__ == "__main__":
    # Altere o caminho abaixo para o seu diretório do catálogo (Windows ou Linux/Termux)
    caminho_do_catalogo = r"F:\Backup Aroni 29-05-2021\Publico\2026\CATALOGO"
    
    # Exemplo para uso em ambiente Linux/Termux:
    # caminho_do_catalogo = "/data/data/com.termux/files/home/catalogo_trofeus"
    
    mapear_catalogo(caminho_do_catalogo)