import bpy
import xml.etree.ElementTree as ET
import re
import os
import mathutils 
import math 
import sys
import shutil
import threading

# ==============================================================================
# 1. CONFIGURAÇÕES E REGRAS GERAIS
# ==============================================================================

REGRAS_MATERIAIS = {    
    # ACRÍLICOS
    '#ed3237': { 'tipo': 'ACRILICO', 'nome_material': 'acrilico_padrão', 'extrusao': 0.001, 'roughness': 0.00, 'transmission': 1.0, 'ior': 1.49 },
    '#fff212': { 'tipo': 'ACRILICO', 'nome_material': 'Acrilico_transparente', 'extrusao': 0.001, 'roughness': 0.01, 'transmission': 1.0, 'ior': 2 },
        
    # MDFs
    '#fefefe': { 'tipo': 'MDF', 'nome_material': 'MDF_3mm', 'extrusao': 0.003, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#e6e7e8': { 'tipo': 'MDF', 'nome_material': 'MDF_6mm', 'extrusao': 0.006, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#d2d3d5': { 'tipo': 'MDF', 'nome_material': 'MDF_9mm', 'extrusao': 0.009, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#373435': { 'tipo': 'PLOTTER', 'nome_material': 'PLOTTER', 'extrusao': 0.0001, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},

    # NOVO MATERIAL: MDF colocado nas costas do troféu (permanece plano/deitado)
    '#00afef': { 'tipo': 'MDF_COSTAS', 'nome_material': 'MDF_Costas_3mm', 'extrusao': 0.003, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15 },

    # RESINA (Área guia sem extrusão)
    '#00a859': { 'tipo': 'RESINA_AREA', 'nome_material': 'Area_Resina', 'extrusao': 0.0, 'roughness': 0.1, 'transmission': 0.2, 'ior': 1.3 },

    # BASES
    "#f58634": { 'tipo': 'BASE', 'nome_material': 'Base_3MM', 'extrusao': 0.005, 'roughness': 0.1, 'transmission': 0.02, 'ior': 1.03},
    "#3e4095": { 'tipo': 'BASE', 'nome_material': 'Base_6MM', 'extrusao': 0.01, 'roughness': 0.1, 'transmission': 0.02, 'ior': 1.03},
    "#f7adaf": { 'tipo': 'BASE', 'nome_material': 'Base_9MM', 'extrusao': 0.015, 'roughness': 0.1, 'transmission': 0.02, 'ior': 1.03},
    "#84716b": { 'tipo': 'BASE', 'nome_material': 'Base_12MM', 'extrusao': 0.12, 'roughness': 0.1, 'transmission': 0.02, 'ior': 1.03},
    
    # ADESIVOS
    '#ec268f': { 'tipo': 'ADESIVO', 'nome_material': 'Adesivo_Padrao', 'extrusao': 0.0001, 'roughness': 0.08, 'transmission': 0.008, 'ior': 1.03 }
}

FATOR_ESCURECIMENTO_ADESIVO = 0.35

# ==============================================================================
# 2. FUNÇÕES AUXILIARES
# ==============================================================================

def hex_para_rgba(hex_color, alpha=1.0):
    if not hex_color or not hex_color.startswith('#'): return (1.0, 1.0, 1.0, alpha)
    hex_color = hex_color.lstrip('#').lower()
    r, g, b = int(hex_color[0:2], 16)/255.0, int(hex_color[2:4], 16)/255.0, int(hex_color[4:6], 16)/255.0
    fator_cmyk = 0.70
    r, g, b = r * fator_cmyk, g * fator_cmyk, b * fator_cmyk
    def srgb_para_linear(c): return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return (srgb_para_linear(r), srgb_para_linear(g), srgb_para_linear(b), alpha)

def obter_caixa_de_colisao(obj):
    bpy.context.view_layer.update()
    cantos = [obj.matrix_world @ mathutils.Vector(v) for v in obj.bound_box]
    xs = [v.x for v in cantos]
    ys = [v.y for v in cantos]
    return min(xs), max(xs), min(ys), max(ys)

def criar_uv_perfeito(obj):
    if not obj.data.uv_layers: obj.data.uv_layers.new(name="UVMap")
    uv_layer = obj.data.uv_layers.active.data
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    if not xs or not ys: return
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    largura = max_x - min_x if max_x > min_x else 0.001
    altura = max_y - min_y if max_y > min_y else 0.001
    for loop in obj.data.loops:
        v = obj.data.vertices[loop.vertex_index]
        u = (v.co.x - min_x) / largura
        v_uv = (v.co.y - min_y) / altura
        uv_layer[loop.index].uv = (u, v_uv)

# ==============================================================================
# 3. MÓDULOS DE PROCESSAMENTO
# ==============================================================================

def carregar_estudio_e_hdri(caminho_blend):
    """Carrega o arquivo de estúdio base e conserta os nós de HDRI do mundo."""
    if caminho_blend and os.path.exists(caminho_blend):
        print(f">>> Carregando estúdio base: {caminho_blend}", flush=True)
        bpy.ops.wm.open_mainfile(filepath=caminho_blend)
        
        if bpy.context.scene.world and bpy.context.scene.world.use_nodes:
            world_node_tree = bpy.context.scene.world.node_tree
            nodes = world_node_tree.nodes
            
            tex_coord = next((n for n in nodes if n.type == 'TEX_COORD'), None)
            mapping = next((n for n in nodes if n.type == 'MAPPING'), None)
            
            if tex_coord and mapping:
                for link in list(world_node_tree.links):
                    if link.to_node == mapping and link.to_socket.name == 'Vector':
                        world_node_tree.links.remove(link)
                world_node_tree.links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])

            for node in nodes:
                if node.type in ['TEX_ENVIRONMENT', 'MAPPING', 'TEX_COORD', 'EMISSION', 'MIX_SHADER', 'LIGHT_PATH', 'RGB']:
                    for inp in node.inputs:
                        if hasattr(inp, 'default_value'):
                            try: inp.default_value = inp.default_value
                            except Exception: pass
            
            world_node_tree.update_tag()
            bpy.context.evaluated_depsgraph_get().update()

def analisar_e_preparar_svg(caminho_svg):
    """Lê o SVG, limpa tags incompatíveis, extrai dados de cor e salva um SVG temporário."""
    print(f">>> Analisando e importando o arquivo SVG...", flush=True)
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    try:
        tree = ET.parse(caminho_svg)
        root = tree.getroot()
    except Exception as e:
        print(f"Erro ao ler SVG: {e}")
        return None, {}, []
    
    imagens_no_svg = []
    elementos_para_remover = []
    dados_extraidos = {}
    contador = 1
    
    for pai in root.iter():
        for filho in list(pai):
            tag_filho = filho.tag.split('}')[-1]
            if tag_filho == 'image':
                for attr, val in filho.attrib.items():
                    if attr.endswith('href') and not val.startswith('data:'):
                        imagens_no_svg.append(val)
                        break
                elementos_para_remover.append((pai, filho))
                continue
            elif tag_filho in ['clipPath', 'mask']:
                elementos_para_remover.append((pai, filho))
                continue
                
            if tag_filho in ['path', 'rect', 'circle', 'ellipse', 'polygon', 'polyline', 'line']:
                style = filho.get('style', '')
                stroke = filho.get('stroke', None)
                fill = filho.get('fill', None)
                
                if style:
                    stroke_match = re.search(r'stroke:\s*([^;]+)', style)
                    if stroke_match and stroke_match.group(1) != 'none': stroke = stroke_match.group(1).strip()
                    fill_match = re.search(r'fill:\s*([^;]+)', style)
                    if fill_match and fill_match.group(1) != 'none': fill = fill_match.group(1).strip()
                
                cor_contorno = ''
                if stroke and stroke != 'none':
                    cor_limpa = stroke.replace('"', '').replace("'", "").replace('\n', '').replace(' ', '').lower()
                    if len(cor_limpa) == 4 and cor_limpa.startswith('#'):
                        cor_limpa = f"#{cor_limpa[1]*2}{cor_limpa[2]*2}{cor_limpa[3]*2}"
                    cor_contorno = cor_limpa

                if cor_contorno and cor_contorno not in REGRAS_MATERIAIS:
                    elementos_para_remover.append((pai, filho))
                elif not cor_contorno:
                    elementos_para_remover.append((pai, filho))
                else:
                    id_obj = f"trofeu_shape_{contador}"
                    filho.set('id', id_obj)
                    contador += 1
                    dados_extraidos[id_obj] = {'contorno': cor_contorno, 'preenchimento': fill if fill else 'Nenhum'}
                    filho.set('fill', '#ffffff') 
                    if 'stroke' in filho.attrib: del filho.attrib['stroke']
                    if 'stroke-width' in filho.attrib: del filho.attrib['stroke-width']
                    if style: 
                        style_limpo = re.sub(r'stroke-[^;]+;?|stroke:[^;]+;?', '', style)
                        style_limpo = re.sub(r'fill:[^;]+;?', '', style_limpo)
                        filho.set('style', style_limpo)

    for pai, filho in elementos_para_remover:
        try: pai.remove(filho)
        except: pass

    pasta_svg = os.path.dirname(caminho_svg)
    nome_arquivo_svg = os.path.splitext(os.path.basename(caminho_svg))[0]
    pasta_imagens = os.path.join(pasta_svg, f"{nome_arquivo_svg}__Images")
    if not os.path.exists(pasta_imagens):
        pasta_imagens = os.path.join(pasta_svg, f"{nome_arquivo_svg}_Images")
        
    imagens_disponiveis = []
    if os.path.exists(pasta_imagens):
        for img_nome in imagens_no_svg:
            caminho_img = os.path.join(pasta_imagens, os.path.basename(img_nome))
            if os.path.exists(caminho_img) and caminho_img not in imagens_disponiveis:
                imagens_disponiveis.append(caminho_img)
        if not imagens_disponiveis:
            for arquivo in os.listdir(pasta_imagens):
                if arquivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                    imagens_disponiveis.append(os.path.join(pasta_imagens, arquivo))
                    
    caminho_temp = os.path.join(pasta_svg, "temp_import.svg")
    tree.write(caminho_temp)
    
    return caminho_temp, dados_extraidos, imagens_disponiveis

def importar_e_converter_svg(caminho_temp):
    """Importa o SVG para o Blender e converte as Curvas em Malhas 3D (Mesh)."""
    objetos_antes = set(bpy.context.scene.objects)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_curve.svg(filepath=caminho_temp)
    objetos_importados = list(set(bpy.context.scene.objects) - objetos_antes)
    
    colecao_ativa = bpy.context.scene.collection
    for obj in objetos_importados:
        obj.hide_set(False)
        obj.hide_viewport = False
        for col in obj.users_collection:
            try: col.objects.unlink(obj)
            except: pass
        if obj.name not in colecao_ativa.objects:
            colecao_ativa.objects.link(obj)

    malhas_convertidas = []
    for obj in objetos_importados:
        if obj.type in ['Curve', 'CURVE']:
            mesh_data = bpy.data.meshes.new_from_object(obj)
            novo_mesh_obj = bpy.data.objects.new(obj.name.replace(".00", "_mesh"), mesh_data)
            novo_mesh_obj.matrix_world = obj.matrix_world.copy()
            
            colecao_ativa.objects.link(novo_mesh_obj)
            bpy.data.objects.remove(obj, do_unlink=True)
            malhas_convertidas.append(novo_mesh_obj)
        elif obj.type == 'MESH':
            malhas_convertidas.append(obj)

    bpy.context.view_layer.update()
    if os.path.exists(caminho_temp): os.remove(caminho_temp)
    return malhas_convertidas

def mapear_e_ordenar_elementos(objetos_importados, dados_extraidos):
    """Associa as regras de material aos objetos e os ordena (Bases primeiro)."""
    def obter_id_numerico(obj):
        match = re.search(r'trofeu_shape_(\d+)', obj.name)
        return int(match.group(1)) if match else 9999

    elementos_mapeados = []
    for idx, obj in enumerate(objetos_importados):
        num_id = obter_id_numerico(obj)
        nome_base = f"trofeu_shape_{num_id}" if num_id != 9999 else f"trofeu_shape_{idx+1}"
        
        dados = dados_extraidos.get(nome_base, {'contorno': '#fefefe', 'preenchimento': 'Nenhum'} )
        cor_contorno = dados.get('contorno', '#fefefe').lower().strip()
        
        if cor_contorno not in REGRAS_MATERIAIS:
            cor_contorno = '#fefefe'
            
        regra = REGRAS_MATERIAIS[cor_contorno]
        tipo_material = regra['tipo']
        eh_base = tipo_material in ['BASE', 'BASE_FINA']
            
        elementos_mapeados.append({
            'obj': obj,
            'nome_base': nome_base,
            'dados': dados,
            'regra': regra,
            'tipo_material': tipo_material,
            'indice_svg': num_id if num_id != 9999 else idx,
            'eh_base': eh_base
        })

    elementos_mapeados.sort(key=lambda x: (0 if x['eh_base'] else 1, x['indice_svg']))
    return elementos_mapeados

def aplicar_materiais_e_empilhar(elementos_mapeados, imagens_disponiveis, usar_verniz):
    """Aplica materiais reutilizando os existentes no .blend para otimizar o tempo de render."""
    print(f">>> Aplicando materiais, texturas e extrusões...", flush=True)
    idx_imagem_global = 0
    suporte_dos_objetos = {}

    for item in elementos_mapeados:
        obj = item['obj']
        nome_base = item['nome_base']
        dados = item['dados']
        regra = item['regra']
        tipo_material = item['tipo_material']

        if tipo_material != 'MDF_COSTAS':
            min_x, max_x, min_y, max_y = obter_caixa_de_colisao(obj)
            pontos_de_teste = []
            matriz, matriz_inv = obj.matrix_world, obj.matrix_world.inverted()
            for v in obj.data.vertices:
                pontos_de_teste.append(( (matriz @ v.co).x, (matriz @ v.co).y ))
            
            passo_x = (max_x - min_x)/10.0 if max_x > min_x else 0.001
            passo_y = (max_y - min_y)/10.0 if max_y > min_y else 0.001
            for i in range(11):
                for j in range(11):
                    px, py = min_x + (i*passo_x), min_y + (j*passo_y)
                    or_loc = matriz_inv @ mathutils.Vector((px, py, 1.0))
                    tg_loc = matriz_inv @ mathutils.Vector((px, py, 0.0))
                    if obj.ray_cast(or_loc, (tg_loc - or_loc).normalized())[0]:
                        pontos_de_teste.append((px, py))

            depsgraph = bpy.context.evaluated_depsgraph_get()
            obj.hide_set(True)
            bpy.context.view_layer.update()
            altura_alvo_z = 0.0
            objeto_abaixo = None 
            
            for px, py in pontos_de_teste:
                ray_scene = bpy.context.scene.ray_cast(depsgraph, mathutils.Vector((px, py, 10.0)), mathutils.Vector((0, 0, -1)))
                if ray_scene[0] and ray_scene[1].z >= altura_alvo_z:
                    altura_alvo_z = ray_scene[1].z
                    objeto_abaixo = ray_scene[4] 
                        
            obj.hide_set(False)
            obj.location.z = altura_alvo_z
            suporte_dos_objetos[obj.name] = objeto_abaixo.name if objeto_abaixo else None
        
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.update()

        if tipo_material == 'ADESIVO': criar_uv_perfeito(obj)
        if regra['extrusao'] > 0:
            mod_solidify = obj.modifiers.new(name="extrusao", type='SOLIDIFY')
            mod_solidify.thickness = regra['extrusao']
            mod_solidify.offset = 1.0 
            mod_solidify.use_even_offset = True    
            mod_solidify.use_quality_normals = True 
            mod_solidify.solidify_mode = 'NON_MANIFOLD' 
            try:
                bpy.ops.object.modifier_apply(modifier=mod_solidify.name)
            except RuntimeError:
                depsgraph_eval = bpy.context.evaluated_depsgraph_get()
                object_eval = obj.evaluated_get(depsgraph_eval)
                mesh_eval = bpy.data.meshes.new_from_object(object_eval)
                obj.modifiers.remove(mod_solidify)
                obj.data = mesh_eval
                bpy.context.view_layer.update()
        
        # OTIMIZAÇÃO DE MATERIAIS: Tenta reutilizar materiais existentes no Blender
        obj.data.materials.clear()
        preenchimento_val = dados.get('preenchimento', 'Nenhum')
        nome_mat_unico = f"Mat_{regra['nome_material']}_{preenchimento_val.replace('#', '')}"
        if tipo_material == 'ADESIVO': 
            nome_mat_unico = f"Mat_Adesivo_{nome_base}"

        mat = bpy.data.materials.get(nome_mat_unico)
        
        if not mat:
            mat = bpy.data.materials.new(name=nome_mat_unico)
            mat.use_nodes = True
            nodes, links = mat.node_tree.nodes, mat.node_tree.links

            if tipo_material == 'ACRILICO':
                node_principled = nodes.get("Principled BSDF")
                if node_principled: nodes.remove(node_principled)
                bsdf = nodes.new('ShaderNodeBsdfGlossy')
                bsdf.location = (10, 300)
                node_output = nodes.get("Material Output")
                links.new(bsdf.outputs['BSDF'], node_output.inputs['Surface'])
                pino_cor = 'Color' 
            else:
                bsdf = nodes.get("Principled BSDF")
                pino_cor = 'Base Color' 

            cor_svg = hex_para_rgba(preenchimento_val) if preenchimento_val != 'Nenhum' else (0.8, 0.6, 0.4, 1.0)

            if tipo_material == 'ADESIVO' and imagens_disponiveis:
                caminho_imagem = imagens_disponiveis[idx_imagem_global % len(imagens_disponiveis)]
                idx_imagem_global += 1 
                img_nome_arquivo = os.path.basename(caminho_imagem)
                img_blender = bpy.data.images.get(img_nome_arquivo) or (bpy.data.images.load(filepath=caminho_imagem) if os.path.exists(caminho_imagem) else None)
                
                tex_node = nodes.new('ShaderNodeTexImage')
                if img_blender: tex_node.image = img_blender
                tex_node.location = (-600, 300)

                hsv_node = nodes.new(type="ShaderNodeHueSaturation")
                hsv_node.location = (-300, 300)
                hsv_node.inputs['Value'].default_value = FATOR_ESCURECIMENTO_ADESIVO
                
                links.new(tex_node.outputs['Color'], hsv_node.inputs['Color'])
                links.new(hsv_node.outputs['Color'], bsdf.inputs[pino_cor])
            else:
                if preenchimento_val != 'Nenhum':
                    if tipo_material == 'ADESIVO':
                        cor_escurecida = (cor_svg[0]*FATOR_ESCURECIMENTO_ADESIVO, cor_svg[1]*FATOR_ESCURECIMENTO_ADESIVO, cor_svg[2]*FATOR_ESCURECIMENTO_ADESIVO, cor_svg[3])
                        bsdf.inputs[pino_cor].default_value = cor_escurecida
                    else:
                        bsdf.inputs[pino_cor].default_value = cor_svg
            
            roughness_final = 0.03 if (usar_verniz and tipo_material in ['MDF', 'MDF_COSTAS']) else regra['roughness']
            if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = roughness_final

            if tipo_material != 'ACRILICO':
                if 'Transmission Weight' in bsdf.inputs: bsdf.inputs['Transmission Weight'].default_value = regra.get('transmission', 0.0)
                elif 'Transmission' in bsdf.inputs: bsdf.inputs['Transmission'].default_value = regra.get('transmission', 0.0)
                if 'IOR' in bsdf.inputs and 'ior' in regra: bsdf.inputs['IOR'].default_value = regra['ior']

        obj.data.materials.append(mat)
        bpy.context.view_layer.update()

    return suporte_dos_objetos

def erguer_corpo_principal_do_trofeu(elementos_mapeados, suporte_dos_objetos):
    """Identifica quais peças não são base e as rotaciona 90 graus para a vertical."""
    def esta_apoiado_na_base(obj_name):
        atual = obj_name
        visitados = set() 
        while atual and atual not in visitados:
            visitados.add(atual)
            for item in elementos_mapeados:
                try:
                    if item['obj'] and item['obj'].name == atual:
                        if item['tipo_material'] in ['BASE', 'BASE_FINA']: return True 
                        elif item['tipo_material'] in ['MDF', 'MDF_COSTAS']: return False 
                except (ReferenceError, AttributeError): continue
            atual = suporte_dos_objetos.get(atual)
        return False

    pecas_corpo = []
    status_rotacao = {}

    for item in elementos_mapeados:
        try:
            obj = item['obj']
            if not obj or obj.name not in bpy.data.objects: continue

            t_mat = item['tipo_material']
            nome_obj = obj.name
            deve_rotacionar = True 
            abaixo = suporte_dos_objetos.get(nome_obj)
            
            apoiado_direto_na_base = False
            if abaixo:
                for i in elementos_mapeados:
                    try:
                        if i['obj'] and i['obj'].name == abaixo and i['tipo_material'] in ['BASE', 'BASE_FINA']:
                            apoiado_direto_na_base = True
                            break
                    except ReferenceError: continue

            if t_mat in ['BASE', 'BASE_FINA', 'MDF_COSTAS']: deve_rotacionar = False  
            elif t_mat in ['ACRILICO', 'ADESIVO', 'RESINA_AREA']:
                if apoiado_direto_na_base or esta_apoiado_na_base(nome_obj): deve_rotacionar = False
                elif abaixo and abaixo in status_rotacao and not status_rotacao[abaixo]: deve_rotacionar = False
                else: deve_rotacionar = True
            else:
                if abaixo and abaixo in status_rotacao and not status_rotacao[abaixo]: deve_rotacionar = True

            status_rotacao[nome_obj] = deve_rotacionar
            if deve_rotacionar: pecas_corpo.append(obj)
        except (ReferenceError, AttributeError): pass

    if pecas_corpo:
        bpy.context.view_layer.update() 
        min_y = min_z = float('inf')
        for obj in pecas_corpo:
            for v in obj.bound_box:
                coord = obj.matrix_world @ mathutils.Vector(v)
                if coord.y < min_y: min_y = coord.y
                if coord.z < min_z: min_z = coord.z
        pivo = mathutils.Vector((0.0, min_y, min_z))
        mat_ida = mathutils.Matrix.Translation(pivo)
        mat_rotacao = mathutils.Matrix.Rotation(math.radians(90), 4, 'X')
        mat_volta = mathutils.Matrix.Translation(-pivo)
        matriz_final = mat_ida @ mat_rotacao @ mat_volta
        for obj in pecas_corpo:
            obj.matrix_world = matriz_final @ obj.matrix_world

    print("Troféu base montado e alinhado com sucesso!", flush=True)
    return pecas_corpo

def processar_mdf_costas(elementos_mapeados, pecas_corpo, suporte_dos_objetos):
    """Posiciona o MDF Costas e a Pista de forma plana na traseira do troféu."""
    for item in elementos_mapeados:
        if item['tipo_material'] == 'MDF_COSTAS':
            obj_costas = item['obj']
            if not obj_costas or obj_costas.name not in bpy.data.objects: continue
                
            bpy.context.view_layer.update()
            obj_costas.hide_set(False)
            obj_costas.hide_viewport = False
            
            bpy.ops.object.select_all(action='DESELECT')
            obj_costas.select_set(True)
            bpy.context.view_layer.objects.active = obj_costas
            bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
            bpy.context.view_layer.update()

            pecas_rotacionadas = [p for p in pecas_corpo if p and p.name in bpy.data.objects]
            
            if pecas_rotacionadas:
                max_y_traseiro = float('-inf')
                for p_obj in pecas_rotacionadas:
                    cantos_p = [p_obj.matrix_world @ mathutils.Vector(v) for v in p_obj.bound_box]
                    max_y_traseiro = max(max_y_traseiro, max(v.y for v in cantos_p))
                
                cantos_costas = [obj_costas.matrix_world @ mathutils.Vector(v) for v in obj_costas.bound_box]
                min_y_costas = min(v.y for v in cantos_costas)
                
                min_y_global_svg = min(min(v.y for v in [p.matrix_world @ mathutils.Vector(v_b) for v_b in p.bound_box]) for p in pecas_rotacionadas)
                altura_z = abs(min_y_costas - min_y_global_svg)
                
                old_y = obj_costas.location.y
                old_z = obj_costas.location.z
                
                obj_costas.location.y += (max_y_traseiro - min_y_costas) + 0.001
                obj_costas.location.z = altura_z
                bpy.context.view_layer.update()
                
                delta_y = obj_costas.location.y - old_y
                delta_z = obj_costas.location.z - old_z
                
                for item_dep in elementos_mapeados:
                    if item_dep['obj'] and suporte_dos_objetos.get(item_dep['obj'].name) == obj_costas.name:
                        obj_filho = item_dep['obj']
                        obj_filho.location.y += delta_y
                        obj_filho.location.z += delta_z
                        bpy.context.view_layer.update()

def processar_resina_3d(elementos_mapeados, suporte_dos_objetos, caminho_modelo_resina, objetos_importados):
    """Importa o modelo 3D da resina, ajusta material e posiciona dinamicamente sobre o suporte correto."""
    dados_resina_pendente = next((i for i in elementos_mapeados if i['tipo_material'] == 'RESINA_AREA'), None)

    if not dados_resina_pendente or not caminho_modelo_resina or not os.path.exists(caminho_modelo_resina):
        return

    obj_marcado_svg = dados_resina_pendente['obj']
    if not obj_marcado_svg or obj_marcado_svg.name not in bpy.data.objects: return
        
    bpy.context.view_layer.update()
    sup_nome = suporte_dos_objetos.get(obj_marcado_svg.name)
    obj_sup = bpy.data.objects.get(sup_nome) if sup_nome else None

    rot_z_original = obj_marcado_svg.rotation_euler.z

    cantos_guia = [obj_marcado_svg.matrix_world @ mathutils.Vector(v) for v in obj_marcado_svg.bound_box]
    dx = max(v.x for v in cantos_guia) - min(v.x for v in cantos_guia)
    dy = max(v.y for v in cantos_guia) - min(v.y for v in cantos_guia)
    dz = max(v.z for v in cantos_guia) - min(v.z for v in cantos_guia)
    
    dimensoes = sorted([dx, dy, dz], reverse=True)
    largura_svg = dimensoes[0]
    altura_svg = dimensoes[1]
    
    centro_x_guia = sum(v.x for v in cantos_guia) / 8.0
    centro_y_guia = sum(v.y for v in cantos_guia) / 8.0
    centro_z_guia = sum(v.z for v in cantos_guia) / 8.0

    extensao = os.path.splitext(caminho_modelo_resina)[1].lower()
    objs_antes_import = set(bpy.context.scene.objects)
    
    try:
        if extensao in ['.obj', '.wavefront']:
            try: bpy.ops.import_scene.obj(filepath=caminho_modelo_resina)
            except AttributeError:
                janelas = bpy.context.window_manager.windows
                if janelas:
                    window = janelas[0]
                    area_3d = next((a for a in window.screen.areas if a.type == 'VIEW_3D'), window.screen.areas[0])
                    with bpy.context.temp_override(window=window, area=area_3d):
                        bpy.ops.wm.obj_import(filepath=caminho_modelo_resina)
                else:
                    bpy.ops.wm.obj_import(filepath=caminho_modelo_resina)
        elif extensao == '.fbx': bpy.ops.import_scene.fbx(filepath=caminho_modelo_resina, use_custom_props=False)
        elif extensao == '.stl': bpy.ops.wm.stl_import(filepath=caminho_modelo_resina)
        elif extensao == '.blend':
            with bpy.data.libraries.load(caminho_modelo_resina, link=False) as (data_from, data_to):
                data_to.objects = data_from.objects
            for obj_carregado in data_to.objects:
                if obj_carregado: bpy.context.scene.collection.objects.link(obj_carregado)
    except Exception as e_import:
        print(f"❌ Erro ao importar resina: {e_import}", flush=True)

    novos_objs = list(set(bpy.context.scene.objects) - objs_antes_import)
    malhas_resina = [o for o in novos_objs if o.type == 'MESH']
    
    if malhas_resina:
        resina_3d_obj = malhas_resina[0]
        
        preenchimento_val = dados_resina_pendente['dados'].get('preenchimento', 'Nenhum')
        regra_resina = dados_resina_pendente['regra']
        resina_3d_obj.data.materials.clear()
        nome_mat_resina = f"Mat_Resina_{dados_resina_pendente['nome_base']}"
        mat_resina = bpy.data.materials.new(name=nome_mat_resina)
        mat_resina.use_nodes = True
        nodes = mat_resina.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if bsdf:
            if preenchimento_val != 'Nenhum': bsdf.inputs['Base Color'].default_value = hex_para_rgba(preenchimento_val)
            if 'Roughness' in bsdf.inputs: bsdf.inputs['Roughness'].default_value = regra_resina.get('roughness', 0.05)
            if 'Transmission Weight' in bsdf.inputs: bsdf.inputs['Transmission Weight'].default_value = regra_resina.get('transmission', 0.9)
            elif 'Transmission' in bsdf.inputs: bsdf.inputs['Transmission'].default_value = regra_resina.get('transmission', 0.9)
            if 'IOR' in bsdf.inputs and 'ior' in regra_resina: bsdf.inputs['IOR'].default_value = regra_resina['ior']
        
        resina_3d_obj.data.materials.append(mat_resina)
        resina_3d_obj.hide_set(False)
        resina_3d_obj.hide_viewport = False
        bpy.ops.object.select_all(action='DESELECT')
        resina_3d_obj.select_set(True)
        bpy.context.view_layer.objects.active = resina_3d_obj
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
        bpy.context.view_layer.update()

        eh_na_base = False
        sup_atual = obj_marcado_svg.name
        visitados = set()
        while sup_atual and sup_atual not in visitados:
            visitados.add(sup_atual)
            pai_nome = suporte_dos_objetos.get(sup_atual)
            if pai_nome:
                item_pai = next((i for i in elementos_mapeados if i['obj'] and i['obj'].name == pai_nome), None)
                if item_pai and 'BASE' in item_pai['tipo_material'].upper():
                    eh_na_base = True
                    break
                sup_atual = pai_nome
            else: break

        correcao_frente = 0.0

        if eh_na_base:
            resina_3d_obj.rotation_euler = (math.radians(89.5), 0.0, rot_z_original + correcao_frente)
            bpy.context.view_layer.update()

            cantos_kart = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
            larg_kart = max(v.x for v in cantos_kart) - min(v.x for v in cantos_kart)
            prof_kart = max(v.y for v in cantos_kart) - min(v.y for v in cantos_kart)

            if larg_kart > 0.0001 and prof_kart > 0.0001:
                escala = min(largura_svg / larg_kart, altura_svg / prof_kart)
                resina_3d_obj.scale = (resina_3d_obj.scale.x * escala, resina_3d_obj.scale.y * escala, resina_3d_obj.scale.z * escala)
                bpy.context.view_layer.update()

            cantos_finais = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
            cx = sum(v.x for v in cantos_finais) / 8.0
            cy = sum(v.y for v in cantos_finais) / 8.0
            min_z_res = min(v.z for v in cantos_finais)
            max_z_sup = max((obj_sup.matrix_world @ mathutils.Vector(v)).z for v in obj_sup.bound_box) if obj_sup else centro_z_guia

            resina_3d_obj.location.x += (centro_x_guia - cx)
            resina_3d_obj.location.y += (centro_y_guia - cy)
            resina_3d_obj.location.z += (max_z_sup - min_z_res) + 0.001

        else:
            resina_3d_obj.rotation_euler = (math.radians(90), 0.0, rot_z_original + correcao_frente)
            bpy.context.view_layer.update()

            cantos_kart = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
            larg_kart = max(v.x for v in cantos_kart) - min(v.x for v in cantos_kart)
            alt_kart = max(v.z for v in cantos_kart) - min(v.z for v in cantos_kart)

            if larg_kart > 0.0001 and alt_kart > 0.0001:
                escala = min(largura_svg / larg_kart, altura_svg / alt_kart)
                resina_3d_obj.scale = (resina_3d_obj.scale.x * escala, resina_3d_obj.scale.y * escala, resina_3d_obj.scale.z * escala)
                bpy.context.view_layer.update()

            cantos_finais = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
            cx = sum(v.x for v in cantos_finais) / 8.0
            cz = sum(v.z for v in cantos_finais) / 8.0
            max_y_res = max(v.y for v in cantos_finais)
            min_y_sup = min((obj_sup.matrix_world @ mathutils.Vector(v)).y for v in obj_sup.bound_box) if obj_sup else centro_y_guia

            resina_3d_obj.location.x += (centro_x_guia - cx)
            resina_3d_obj.location.z += (centro_z_guia - cz)
            resina_3d_obj.location.y += (min_y_sup - max_y_res) - 0.001

        bpy.context.view_layer.update()
        objetos_importados.append(resina_3d_obj)

    try:
        if obj_marcado_svg and obj_marcado_svg.name in bpy.data.objects:
            bpy.data.objects.remove(obj_marcado_svg, do_unlink=True)
    except (ReferenceError, KeyError): pass

def configurar_cameras(objetos_importados):
    """Posiciona iluminação e câmeras automaticamente focando estritamente nas malhas do troféu e da resina."""
    
    # 1. Filtra estritamente as malhas que pertencem ao troféu/resina 
    # (Descarta objetos de cenário, chão e paredes do estúdio base)
    objetos_validos_cena = []
    
    # Tenta usar a lista de objetos importados/criados no fluxo
    for obj in objetos_importados:
        try:
            if obj and hasattr(obj, "name") and obj.name in bpy.data.objects and obj.type == 'MESH':
                # Evita pegar malhas do estúdio
                nome_lc = obj.name.lower()
                if not any(ign in nome_lc for ign in ["estudio", "chao", "ground", "studio", "wall", "fundo", "cenario"]):
                    objetos_validos_cena.append(obj)
        except (ReferenceError, RuntimeError):
            continue

    # Fallback: Se a lista direta falhar, busca na cena apenas malhas do troféu
    if not objetos_validos_cena:
        for obj in bpy.context.scene.objects:
            try:
                if obj.type == 'MESH' and not obj.hide_get() and hasattr(obj, "bound_box"):
                    nome_lc = obj.name.lower()
                    if not any(ign in nome_lc for ign in ["estudio", "chao", "ground", "studio", "wall", "fundo", "cenario"]):
                        objetos_validos_cena.append(obj)
            except (ReferenceError, RuntimeError):
                continue

    if not objetos_validos_cena:
        print("⚠️ Nenhuma malha do troféu encontrada para enquadramento das câmeras.", flush=True)
        return []

    bpy.context.view_layer.update()
    render = bpy.context.scene.render
    render.resolution_x = 1080
    render.resolution_y = 1350
    aspect_ratio = render.resolution_x / render.resolution_y
    
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    # 2. Varredura das coordenadas extremas reais APENAS das peças do troféu
    for obj in objetos_validos_cena:
        try:
            for v in obj.bound_box:
                coord = obj.matrix_world @ mathutils.Vector(v)
                min_x = min(min_x, coord.x)
                max_x = max(max_x, coord.x)
                min_y = min(min_y, coord.y)
                max_y = max(max_y, coord.y)
                min_z = min(min_z, coord.z)
                max_z = max(max_z, coord.z)
        except (ReferenceError, RuntimeError):
            continue

    if min_x == float('inf') or max_z == float('-inf'):
        print("⚠️ Não foi possível calcular o centro dos objetos.", flush=True)
        return []

    # 3. Ponto focal central e dimensões reais do troféu
    alvo_centro = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
    tamanho_x, tamanho_y, tamanho_z = max_x - min_x, max_y - min_y, max_z - min_z

    dummy_cam_data = bpy.data.cameras.new("temp_cam")
    fov = dummy_cam_data.angle
    bpy.data.cameras.remove(dummy_cam_data)

    # Considera a proporção vertical 4x5
    tamanho_real = max(tamanho_z, tamanho_x / aspect_ratio) if aspect_ratio > 1 else max(tamanho_x, tamanho_z * aspect_ratio)
    
    # MARGEM DE ENQUADRAMENTO: 1.22 deixa o troféu bem próximo e preenchendo a tela do render
    MARGEM_ENQUADRAMENTO = 1.3
    distancia_base = (tamanho_real / 2.0) / math.tan(fov / 2.0) * MARGEM_ENQUADRAMENTO

    ponto_focal_alvo = alvo_centro.copy()   
    ponto_focal_alvo.z += tamanho_z * 0.00  # Foco levemente acima do centro geométrico
    altura_camera = alvo_centro.z + (tamanho_z * 0.15)  # Elevação suave da lente

    # 4. Criando e apontando as 3 câmeras
    def criar_e_apontar_camera(nome, local_vetor, focal_vetor):
        cam_obj = bpy.data.objects.get(nome)
        if not cam_obj:
            cam_data = bpy.data.cameras.new(name=nome)
            cam_obj = bpy.data.objects.new(nome, cam_data)
            bpy.context.scene.collection.objects.link(cam_obj)
        cam_obj.data.type = 'PERSP'
        cam_obj.location = local_vetor
        direcao = focal_vetor - cam_obj.location
        cam_obj.rotation_euler = direcao.to_track_quat('-Z', 'Y').to_euler()
        return cam_obj

    pos_cam_principal = mathutils.Vector((alvo_centro.x, min_y - distancia_base, altura_camera))
    cam_principal = criar_e_apontar_camera("Camera_Principal", pos_cam_principal, ponto_focal_alvo)

    angulo_diag = math.radians(35)
    dist_lateral = distancia_base * 1.05

    criar_e_apontar_camera(
        "Camera_Esquerda",
        mathutils.Vector((alvo_centro.x - (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)),
        ponto_focal_alvo
    )
    
    criar_e_apontar_camera(
        "Camera_Direita",
        mathutils.Vector((alvo_centro.x + (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)),
        ponto_focal_alvo
    )

    bpy.context.scene.camera = cam_principal
    print(f"📷 Câmeras enquadradas com sucesso! Distância calculada do troféu: {distancia_base:.2f}m", flush=True)

    return ["Camera_Principal", "Camera_Esquerda", "Camera_Direita"]

def renderizar_cena(cameras_nomes, pasta_saida_renders, cycles_samples):
    """Configura o Cycles e roda os Renders para cada câmera."""
    pasta_dest = pasta_saida_renders
    if not os.path.exists(pasta_dest): os.makedirs(pasta_dest)
    
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    
    try:
        cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
        cycles_prefs.compute_device_type = 'NONE'
        scene.cycles.device = 'CPU'
    except Exception: pass
        
    total_samples = int(cycles_samples)
    scene.cycles.samples = total_samples
    scene.cycles.use_denoising = True

    cameras_validas = [(nome, bpy.data.objects.get(nome)) for nome in cameras_nomes if bpy.data.objects.get(nome)]

    for idx_cam, (nome_cam, cam) in enumerate(cameras_validas):
        scene.camera = cam
        scene.render.filepath = os.path.join(pasta_dest, f"{nome_cam}.png")
        print(f">>> Renderizando câmera: {nome_cam} via Cycles...", flush=True)
        
        import time
        parar_thread = threading.Event()
        def atualizar_progresso_fluido():
            atual = 0
            while not parar_thread.is_set() and atual < max(1, total_samples - 2):
                atual += 1
                print(f"[SAMPLE_PROGRESS] {atual}/{total_samples}|CAM:{nome_cam}", flush=True)
                time.sleep(0.08)

        t_prog = threading.Thread(target=atualizar_progresso_fluido, daemon=True)
        t_prog.start()
        bpy.ops.render.render(write_still=True)
        parar_thread.set()
        t_prog.join(timeout=0.5)
        print(f"[SAMPLE_PROGRESS] {total_samples}/{total_samples}|CAM:{nome_cam}", flush=True)

    print(f"Renders salvos em: {pasta_dest}", flush=True)

# ==============================================================================
# 4. FUNÇÃO PRINCIPAL (ORQUESTRADOR)
# ==============================================================================

def processar_svg_no_blender(caminho_svg, pasta_saida_renders, caminho_blend="", renderizar=True, usar_textura=True, cycles_samples=128, usar_verniz=False, caminho_modelo_resina=""):
    
    carregar_estudio_e_hdri(caminho_blend)
    caminho_temp, dados_extraidos, imagens_disponiveis = analisar_e_preparar_svg(caminho_svg)
    if not caminho_temp: return
    
    objetos_importados = importar_e_converter_svg(caminho_temp)
    elementos_mapeados = mapear_e_ordenar_elementos(objetos_importados, dados_extraidos)
    suporte_dos_objetos = aplicar_materiais_e_empilhar(elementos_mapeados, imagens_disponiveis, usar_verniz)
    pecas_corpo = erguer_corpo_principal_do_trofeu(elementos_mapeados, suporte_dos_objetos)
    processar_mdf_costas(elementos_mapeados, pecas_corpo, suporte_dos_objetos)
    processar_resina_3d(elementos_mapeados, suporte_dos_objetos, caminho_modelo_resina, objetos_importados)

    cameras_nomes = configurar_cameras(objetos_importados)

    if renderizar and pasta_saida_renders and cameras_nomes:
        renderizar_cena(cameras_nomes, pasta_saida_renders, cycles_samples)
    else:
        print(">>> Modo interativo ativo: O Blender permaneceu aberto com o troféu montado.", flush=True)


if __name__ == "__main__":
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
        caminho_svg = argv[0] if len(argv) > 0 else ""
        pasta_saida = argv[1] if len(argv) > 1 else ""
        caminho_blend = argv[2] if len(argv) > 2 else ""
        
        renderizar_automaticamente = True
        if len(argv) > 3: renderizar_automaticamente = argv[3].strip().lower() in ['true', '1', 'yes']
            
        usar_textura = True
        if len(argv) > 4: usar_textura = argv[4].strip().lower() in ['true', '1', 'yes']
            
        cycles_samples = 128
        if len(argv) > 5:
            try: cycles_samples = int(argv[5])
            except: cycles_samples = 128
            
        usar_verniz = False
        if len(argv) > 6: usar_verniz = argv[6].strip().lower() in ['true', '1', 'yes']
            
        caminho_modelo_resina = ""
        if len(argv) > 7: caminho_modelo_resina = argv[7]
            
        processar_svg_no_blender(caminho_svg, pasta_saida, caminho_blend, renderizar_automaticamente, usar_textura, cycles_samples, usar_verniz, caminho_modelo_resina)