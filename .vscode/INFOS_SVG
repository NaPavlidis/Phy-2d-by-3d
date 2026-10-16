import os
import re
import math
import xml.etree.ElementTree as ET

try:
    from svgpathtools import parse_path
    HAS_SVGPATH = True
except ImportError:
    HAS_SVGPATH = False

CAMINHO_TROFÉUS = R"F:\\Backup Aroni 29-05-2021\\Publico\\2026\\CATALOGO\\KART\KAR25001\\SVG\\KAR25001.svg"


# ==============================================================================
# DICIONÁRIO COMPLETO DE MATERIAIS
# ==============================================================================
MAPA_MATERIAIS = {
    '#ed3237': {'tipo': 'ACRILICO', 'nome_material': 'acrilico_padrão'},
    '#fff212': {'tipo': 'ACRILICO', 'nome_material': 'Acrilico_transparente'},
    '#d2ae6d': {'tipo': 'ACRILICO_ESPELHADO', 'nome_material': 'Acrilico_Espelhado_Dourado'},
    '#fefefe': {'tipo': 'MDF', 'nome_material': 'MDF_3mm'},
    '#e6e7e8': {'tipo': 'MDF', 'nome_material': 'MDF_6mm'},
    '#d2d3d5': {'tipo': 'MDF', 'nome_material': 'MDF_9mm'},
    '#373435': {'tipo': 'PLOTTER', 'nome_material': 'PLOTTER'},
    '#00afef': {'tipo': 'MDF_COSTAS', 'nome_material': 'MDF_Costas_3mm'},
    '#00a859': {'tipo': 'RESINA', 'nome_material': 'RESINA 3D'},
    '#f58634': {'tipo': 'BASE', 'nome_material': 'Base_3MM'},
    '#3e4095': {'tipo': 'BASE', 'nome_material': 'Base_6MM'},
    '#f7adaf': {'tipo': 'BASE', 'nome_material': 'Base_9MM'},
    '#84716b': {'tipo': 'BASE', 'nome_material': 'Base_12MM'},
    '#ec268f': {'tipo': 'ADESIVO', 'nome_material': 'Adesivo_Padrao'}
}


def hex_para_rgb(hex_str):
    hex_str = hex_str.lstrip('#').strip()
    if len(hex_str) == 3:
        hex_str = ''.join([c*2 for c in hex_str])
    if len(hex_str) != 6:
        return (0, 0, 0)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))


def identificar_material(cor_hex):
    if not cor_hex or cor_hex == 'none':
        return None

    cor_clean = cor_hex.strip().lower()

    if cor_clean in MAPA_MATERIAIS:
        return MAPA_MATERIAIS[cor_clean]

    rgb_alvo = hex_para_rgb(cor_clean)
    menor_distancia = float('inf')
    melhor_match = None

    for hex_mapa, dados in MAPA_MATERIAIS.items():
        rgb_mapa = hex_para_rgb(hex_mapa)
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(rgb_alvo, rgb_mapa)))
        if dist < menor_distancia:
            menor_distancia = dist
            melhor_match = dados

    if menor_distancia < 45.0:
        return melhor_match

    return {'tipo': 'OUTRO', 'nome_material': f'Cor_Desconhecida_{cor_clean}'}


def extrair_classes_css(root):
    mapa_css = {}
    for style_elem in root.iter('{http://www.w3.org/2000/svg}style'):
        text = style_elem.text or ''
        regras = re.findall(r'\.([\w-]+)\s*\{([^}]+)\}', text)
        for classe, props in regras:
            dic_props = {}
            for item in props.split(';'):
                if ':' in item:
                    k, v = item.split(':', 1)
                    dic_props[k.strip().lower()] = v.strip().lower()
            mapa_css[classe] = dic_props
    return mapa_css


def extrair_informacoes_svg(caminho_svg):
    if not os.path.exists(caminho_svg):
        print(f"❌ Erro: O arquivo '{caminho_svg}' não foi encontrado no caminho especificado.")
        return

    nome_arquivo = os.path.basename(caminho_svg)

    try:
        tree = ET.parse(caminho_svg)
        root = tree.getroot()
    except Exception as e:
        print(f"❌ Erro ao ler o arquivo SVG: {e}")
        return

    mapa_css = extrair_classes_css(root)
    materiais_qtd = {}

    vb = root.attrib.get('viewBox', '').split()
    vb_w = float(vb[2]) if len(vb) == 4 else 0.0
    vb_h = float(vb[3]) if len(vb) == 4 else 0.0

    width_str = root.attrib.get('width', '')
    
    if 'mm' in width_str and vb_w > 0:
        val_w = float(re.sub(r'[^\d.]', '', width_str))
        fator_mm = val_w / vb_w
    else:
        # Padrão de precisão do CorelDRAW (0.1 mm por unidade de coordenadas)
        fator_mm = 0.1

    re_coords = re.compile(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?')

    def obter_cor_elemento(elem):
        stroke, fill = '', ''

        classe = elem.attrib.get('class', '')
        if classe in mapa_css:
            stroke = mapa_css[classe].get('stroke', '')
            fill = mapa_css[classe].get('fill', '')

        stroke = elem.attrib.get('stroke', stroke)
        fill = elem.attrib.get('fill', fill)
        style = elem.attrib.get('style', '')

        if 'stroke:' in style:
            m = re.search(r'stroke:\s*([^;]+)', style)
            if m: stroke = m.group(1).strip()

        if 'fill:' in style:
            m = re.search(r'fill:\s*([^;]+)', style)
            if m: fill = m.group(1).strip()

        if stroke and stroke != 'none' and stroke.startswith('#'):
            return stroke.lower()

        if fill and fill != 'none' and fill.startswith('#'):
            return fill.lower()

        return None

    TIPOS_CORPO_EXCLUSIVO = {'ACRILICO', 'ACRILICO_ESPELHADO', 'MDF'}
    pecas_isoladas = []

    for elem in root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

        if tag in ['defs', 'clipPath', 'style', 'metadata', 'svg']:
            continue

        if tag in ['path', 'rect', 'polygon', 'polyline', 'circle', 'ellipse']:
            cor = obter_cor_elemento(elem)
            mat_info = identificar_material(cor)

            if mat_info:
                chave = (mat_info['tipo'], mat_info['nome_material'])
                materiais_qtd[chave] = materiais_qtd.get(chave, 0) + 1

            eh_pagina = False
            if tag == 'rect' and vb_w > 0 and vb_h > 0:
                w = float(elem.attrib.get('width', 0))
                h = float(elem.attrib.get('height', 0))
                if abs(w - vb_w) < 5.0 or abs(h - vb_h) < 5.0:
                    eh_pagina = True

            # DESCOMPOSIÇÃO DE CAMINHO COMPOSTO (SUB-PATHS ISOLADOS)
            if mat_info and mat_info['tipo'] in TIPOS_CORPO_EXCLUSIVO and not eh_pagina:
                if tag == 'path':
                    d = elem.attrib.get('d', '')
                    
                    if HAS_SVGPATH:
                        try:
                            # Divide o caminho composto em sub-caminhos independentes
                            path_obj = parse_path(d)
                            subpaths = path_obj.continuous_subpaths()
                            
                            for sp in subpaths:
                                xmin, xmax, ymin, ymax = sp.bbox()
                                w_mm = (xmax - xmin) * fator_mm
                                h_mm = (ymax - ymin) * fator_mm
                                
                                larg = min(w_mm, h_mm)
                                alt = max(w_mm, h_mm)
                                
                                # Filtra ruídos ou furos internos (< 3cm)
                                if larg > 30.0 and alt > 30.0:
                                    pecas_isoladas.append((larg, alt, mat_info['nome_material']))
                        except:
                            pass
                    else:
                        # Fallback manual por comandos 'M' / 'm'
                        sub_str = re.split(r'(?=[Mm])', d)
                        for sp in sub_str:
                            if not sp.strip():
                                continue
                            coords = [float(v) for v in re_coords.findall(sp)]
                            if len(coords) >= 4:
                                xs = coords[0::2]
                                ys = coords[1::2]
                                w_mm = (max(xs) - min(xs)) * fator_mm
                                h_mm = (max(ys) - min(ys)) * fator_mm
                                larg = min(w_mm, h_mm)
                                alt = max(w_mm, h_mm)
                                if larg > 30.0 and alt > 30.0:
                                    pecas_isoladas.append((larg, alt, mat_info['nome_material']))

                elif tag == 'rect':
                    rw = float(elem.attrib.get('width', 0))
                    rh = float(elem.attrib.get('height', 0))
                    if rw > 0 and rh > 0:
                        w_mm = rw * fator_mm
                        h_mm = rh * fator_mm
                        larg = min(w_mm, h_mm)
                        alt = max(w_mm, h_mm)
                        if larg > 30.0 and alt > 30.0:
                            pecas_isoladas.append((larg, alt, mat_info['nome_material']))

    # Seleciona a maior sub-peça individual do corpo do troféu
    if pecas_isoladas:
        pecas_isoladas.sort(key=lambda p: p[1], reverse=True)
        largura_final_mm, altura_final_mm, nome_chapa_fundo = pecas_isoladas[0]
    else:
        largura_final_mm, altura_final_mm, nome_chapa_fundo = 0.0, 0.0, "N/A"

    largura_final_cm = largura_final_mm / 10.0
    altura_final_cm = altura_final_mm / 10.0

    # Retorno Formatado no Console
    print("\n" + "=" * 65)
    print(" 📊 RELATÓRIO DE ESTRUTURA DO TROFÉU (SVG)")
    print("=" * 65)
    print(f"📁 Nome do Arquivo : {nome_arquivo}")
    print("-" * 65)

    print("📦 MATERIAIS E QUANTIDADES:")
    if materiais_qtd:
        for (tipo, nome), qtd in materiais_qtd.items():
            print(f"   • Tipo: {tipo:<22} | Nome: {nome:<28} | Qtd: {qtd}")
    else:
        print("   • Nenhum material/contorno identificado no arquivo.")

    print("-" * 65)
    print("📐 TAMANHO GERAL (PEÇA INDIVIDUAL DO CORPO):")
    print(f"   • Peça de Fundo: {nome_chapa_fundo}")
    print(f"   • Largura     : {largura_final_mm:.2f} mm ({largura_final_cm:.2f} cm)")
    print(f"   • Altura      : {altura_final_mm:.2f} mm ({altura_final_cm:.2f} cm)")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    caminho_svg = CAMINHO_TROFÉUS
    extrair_informacoes_svg(caminho_svg)