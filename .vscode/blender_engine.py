import bpy
import xml.etree.ElementTree as ET
import re
import os
import mathutils 
import math 
import sys
import shutil
import threading

# --- REGRAS DE MATERIAIS AGRUPADOS POR TIPO ---
REGRAS_MATERIAIS = {    
    # ACRÍLICOS
    '#ed3237': { 'tipo': 'ACRILICO', 'nome_material': 'acrilico_padrão', 'extrusao': 0.001, 'roughness': 0.00, 'transmission': 1.0, 'ior': 1.49 },
    '#fff212': { 'tipo': 'ACRILICO', 'nome_material': 'Acrilico_transparente', 'extrusao': 0.001, 'roughness': 0.01, 'transmission': 1.0, 'ior': 2 },
        
<<<<<<< HEAD
    # MDFs (Qualquer variação de MDF)
=======
    # MDFs
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    '#fefefe': { 'tipo': 'MDF', 'nome_material': 'MDF_3mm', 'extrusao': 0.003, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#e6e7e8': { 'tipo': 'MDF', 'nome_material': 'MDF_6mm', 'extrusao': 0.006, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#d2d3d5': { 'tipo': 'MDF', 'nome_material': 'MDF_9mm', 'extrusao': 0.009, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#373435': { 'tipo': 'PLOTTER', 'nome_material': 'PLOTTER', 'extrusao': 0.0001, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},

<<<<<<< HEAD
    # RESINA (Área guia sem extrusão)
    '#00a859': { 'tipo': 'RESINA_AREA', 'nome_material': 'Area_Resina', 'extrusao': 0.0, 'roughness': 0.0, 'transmission': 0.0 },
=======
   # RESINA (Área guia sem extrusão com IOR e Transmissão configurados)
    '#00a859': { 'tipo': 'RESINA_AREA', 'nome_material': 'Area_Resina', 'extrusao': 0.0, 'roughness': 0.05, 'transmission': 0.2, 'ior': 1 },
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586

    # BASES
    "#f58634": { 'tipo': 'BASE', 'nome_material': 'Base_3MM', 'extrusao': 0.003, 'roughness': 0.2, 'transmission': 0.08, 'ior': 1.15},
    "#3e4095": { 'tipo': 'BASE', 'nome_material': 'Base_6MM', 'extrusao': 0.01, 'roughness': 0.2, 'transmission': 0.08, 'ior': 1.15},
    "#f7adaf": { 'tipo': 'BASE', 'nome_material': 'Base_9MM', 'extrusao': 0.015, 'roughness': 0.2, 'transmission': 0.08, 'ior': 1.15},
    "#84716b": { 'tipo': 'BASE', 'nome_material': 'Base_12MM', 'extrusao': 0.02, 'roughness': 0.2, 'transmission': 0.08, 'ior': 1.15},
    
    # ADESIVOS
    '#ec268f': { 'tipo': 'ADESIVO', 'nome_material': 'Adesivo_Padrao', 'extrusao': 0.0001, 'roughness': 0.05, 'transmission': 0.6, 'ior': 1.2 }
}


def hex_para_rgba(hex_color, alpha=1.0):
    if not hex_color or not hex_color.startswith('#'): return (1.0, 1.0, 1.0, alpha)
    hex_color = hex_color.lstrip('#').lower()
    r, g, b = int(hex_color[0:2], 16)/255.0, int(hex_color[2:4], 16)/255.0, int(hex_color[4:6], 16)/255.0
    fator_cmyk = 0.45
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

def processar_svg_no_blender(caminho_svg, pasta_saida_renders, caminho_blend="", renderizar=True, usar_textura=True, cycles_samples=128, usar_verniz=False, caminho_modelo_resina=""):
<<<<<<< HEAD
=======

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    # 1. Carrega o estúdio base se fornecido
    if caminho_blend and os.path.exists(caminho_blend):
        print(f">>> Carregando estúdio base: {caminho_blend}", flush=True)
        bpy.ops.wm.open_mainfile(filepath=caminho_blend)
        
        # --- CORREÇÃO E ATUALIZAÇÃO COMPLETA DA ÁRVORE DE NÓS DO WORLD ---
        if bpy.context.scene.world and bpy.context.scene.world.use_nodes:
            world_node_tree = bpy.context.scene.world.node_tree
            nodes = world_node_tree.nodes
            
            # A. Corrige a conexão de 'Normal' para 'Generated' no Texture Coordinate
            tex_coord = next((n for n in nodes if n.type == 'TEX_COORD'), None)
            mapping = next((n for n in nodes if n.type == 'MAPPING'), None)
            
            if tex_coord and mapping:
                # Remove conexões antigas do pino de entrada Vector do Mapping
                for link in list(world_node_tree.links):
                    if link.to_node == mapping and link.to_socket.name == 'Vector':
                        world_node_tree.links.remove(link)
                # Conecta Normal -> Vector
                world_node_tree.links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])

            # B. Notifica alterações em todos os tipos de nós usados na sua estrutura
            tipos_nos_world = ['TEX_ENVIRONMENT', 'MAPPING', 'TEX_COORD', 'EMISSION', 'MIX_SHADER', 'LIGHT_PATH', 'RGB']
            for node in nodes:
                if node.type in tipos_nos_world:
                    for inp in node.inputs:
                        if hasattr(inp, 'default_value'):
                            try:
                                inp.default_value = inp.default_value
                            except Exception:
                                pass
            
            # C. Força a atualização de rotação no nó Mapping para recalcular o HDRI no Blender
            if mapping:
                mapping.inputs['Rotation'].default_value[2] += 0.0001
                mapping.inputs['Rotation'].default_value[2] -= 0.0001
            
            world_node_tree.update_tag()
            bpy.context.evaluated_depsgraph_get().update()

    print(f">>> Analisando e importando o arquivo SVG...", flush=True)
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    try:
        tree = ET.parse(caminho_svg)
        root = tree.getroot()
    except Exception as e:
        print(f"Erro ao ler SVG: {e}")
        return
    
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
                    print(f"⚠️ ATENÇÃO: Cor de contorno não encontrada nas REGRAS: {cor_contorno}. O objeto será ignorado.")
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
    
    objetos_antes = set(bpy.context.scene.objects)
    
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_curve.svg(filepath=caminho_temp)
    
    objetos_importados = list(set(bpy.context.scene.objects) - objetos_antes)
    
    colecao_ativa = bpy.context.scene.collection
    for obj in objetos_importados:
        obj.hide_set(False)
        obj.hide_viewport = False
        for col in obj.users_collection:
            try:
                col.objects.unlink(obj)
            except:
                pass
        if obj.name not in colecao_ativa.objects:
            colecao_ativa.objects.link(obj)

    print(f">>> Convertendo curvas e montando camadas 3D...", flush=True)
    malhas_convertidas = []
    for obj in objetos_importados:
        if obj.type == 'Curve' or obj.type == 'CURVE':
            mesh_data = bpy.data.meshes.new_from_object(obj)
            novo_mesh_obj = bpy.data.objects.new(obj.name.replace(".00", "_mesh"), mesh_data)
            novo_mesh_obj.matrix_world = obj.matrix_world.copy()
            
            colecao_ativa.objects.link(novo_mesh_obj)
            bpy.data.objects.remove(obj, do_unlink=True)
            
            bpy.ops.object.select_all(action='DESELECT')
            novo_mesh_obj.select_set(True)
            bpy.context.view_layer.objects.active = novo_mesh_obj
            
            malhas_convertidas.append(novo_mesh_obj)
        elif obj.type == 'MESH':
            malhas_convertidas.append(obj)

    objetos_importados = malhas_convertidas
    bpy.context.view_layer.update()
    
    pasta_script_atual = os.path.dirname(os.path.abspath(__file__))

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

    print(f">>> Aplicando materiais, texturas e adesivos...", flush=True)
    idx_imagem_global = 0
    suporte_dos_objetos = {}
    materiais_criados = {}

<<<<<<< HEAD
    # Dicionário para armazenar e reaproveitar materiais já criados
    materiais_criados = {}

    # --- LOOP DE PROCESSAMENTO E MONTAGEM ORDENADA VIA RAYCAST ---
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    for item in elementos_mapeados:
        obj = item['obj']
        nome_base = item['nome_base']
        dados = item['dados']
        regra = item['regra']
        tipo_material = item['tipo_material']

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

        if tipo_material == 'ADESIVO': 
            criar_uv_perfeito(obj)

<<<<<<< HEAD
        # Modificador de Extrusão (Aplica apenas se houver espessura definida)
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
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
        
        obj.data.materials.clear()

<<<<<<< HEAD
        # --- SISTEMA DE REUSO DE MATERIAIS ---
        preenchimento_val = dados.get('preenchimento', 'Nenhum')
        chave_material = f"{regra['nome_material']}_{preenchimento_val}"

        # Se o material for ADESIVO, geramos individualmente por ter imagem própria
=======
        # REUSO DE MATERIAIS
        preenchimento_val = dados.get('preenchimento', 'Nenhum')
        chave_material = f"{regra['nome_material']}_{preenchimento_val}"

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
        if tipo_material == 'ADESIVO':
            chave_material = f"{regra['nome_material']}_{nome_base}"

        if chave_material in materiais_criados:
<<<<<<< HEAD
            # Reutiliza o material já configurado anteriormente
            mat = materiais_criados[chave_material]
        else:
            # Cria um novo material único para esta cor/tipo
=======
            mat = materiais_criados[chave_material]
        else:
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            nome_mat_unico = f"Mat_{regra['nome_material']}" if tipo_material != 'ADESIVO' else f"Mat_{regra['nome_material']}_{nome_base}"
            mat = bpy.data.materials.new(name=nome_mat_unico)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links

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
<<<<<<< HEAD
=======

            if tipo_material == 'ADESIVO' and imagens_disponiveis:
                caminho_imagem = imagens_disponiveis[idx_imagem_global % len(imagens_disponiveis)]
                idx_imagem_global += 1 
                img_nome_arquivo = os.path.basename(caminho_imagem)
                img_blender = bpy.data.images.get(img_nome_arquivo)
                if not img_blender and os.path.exists(caminho_imagem):
                    img_blender = bpy.data.images.load(filepath=caminho_imagem)
                
                tex_node = nodes.new('ShaderNodeTexImage')
                if img_blender:
                    tex_node.image = img_blender
                tex_node.location = (-600, 300)

                if bpy.app.version >= (3, 4, 0):
                    mix_adesivo = nodes.new('ShaderNodeMix')
                    mix_adesivo.data_type = 'RGBA'
                    mix_adesivo.blend_type = 'MULTIPLY'
                    input_fac_ad = mix_adesivo.inputs.get('Factor', mix_adesivo.inputs[0])
                    input_a_ad = mix_adesivo.inputs.get('A', mix_adesivo.inputs[6])
                    input_b_ad = mix_adesivo.inputs.get('B', mix_adesivo.inputs[7])
                    saida_mix_ad = mix_adesivo.outputs.get('Result', mix_adesivo.outputs[2])
                else:
                    mix_adesivo = nodes.new('ShaderNodeMixRGB')
                    mix_adesivo.blend_type = 'MULTIPLY'
                    input_fac_ad = mix_adesivo.inputs['Fac']
                    input_a_ad = mix_adesivo.inputs['Color1']
                    input_b_ad = mix_adesivo.inputs['Color2']
                    saida_mix_ad = mix_adesivo.outputs['Color']

                mix_adesivo.location = (-300, 300)
                input_fac_ad.default_value = 0.65
                
                links.new(tex_node.outputs['Color'], input_a_ad)
                fator_escuro_cmyk = (0.30, 0.30, 0.30, 0.5)
                input_b_ad.default_value = fator_escuro_cmyk
                links.new(saida_mix_ad, bsdf.inputs[pino_cor])
            else:
                if preenchimento_val != 'Nenhum':
                    bsdf.inputs[pino_cor].default_value = cor_svg
            
            roughness_final = regra['roughness']
            if usar_verniz and tipo_material == 'MDF':
                roughness_final = 0.015

            if 'Roughness' in bsdf.inputs: 
                bsdf.inputs['Roughness'].default_value = roughness_final

            if tipo_material != 'ACRILICO':
                if 'Transmission Weight' in bsdf.inputs: 
                    bsdf.inputs['Transmission Weight'].default_value = regra.get('transmission', 0.0)
                elif 'Transmission' in bsdf.inputs: 
                    bsdf.inputs['Transmission'].default_value = regra.get('transmission', 0.0)
                if 'IOR' in bsdf.inputs and 'ior' in regra:
                    bsdf.inputs['IOR'].default_value = regra['ior']

            materiais_criados[chave_material] = mat
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586

            if tipo_material == 'ADESIVO' and imagens_disponiveis:
                caminho_imagem = imagens_disponiveis[idx_imagem_global % len(imagens_disponiveis)]
                idx_imagem_global += 1 
                img_nome_arquivo = os.path.basename(caminho_imagem)
                img_blender = bpy.data.images.get(img_nome_arquivo)
                if not img_blender and os.path.exists(caminho_imagem):
                    img_blender = bpy.data.images.load(filepath=caminho_imagem)
                
                tex_node = nodes.new('ShaderNodeTexImage')
                if img_blender:
                    tex_node.image = img_blender
                tex_node.location = (-600, 300)

                if bpy.app.version >= (3, 4, 0):
                    mix_adesivo = nodes.new('ShaderNodeMix')
                    mix_adesivo.data_type = 'RGBA'
                    mix_adesivo.blend_type = 'MULTIPLY'
                    input_fac_ad = mix_adesivo.inputs.get('Factor', mix_adesivo.inputs[0])
                    input_a_ad = mix_adesivo.inputs.get('A', mix_adesivo.inputs[6])
                    input_b_ad = mix_adesivo.inputs.get('B', mix_adesivo.inputs[7])
                    saida_mix_ad = mix_adesivo.outputs.get('Result', mix_adesivo.outputs[2])
                else:
                    mix_adesivo = nodes.new('ShaderNodeMixRGB')
                    mix_adesivo.blend_type = 'MULTIPLY'
                    input_fac_ad = mix_adesivo.inputs['Fac']
                    input_a_ad = mix_adesivo.inputs['Color1']
                    input_b_ad = mix_adesivo.inputs['Color2']
                    saida_mix_ad = mix_adesivo.outputs['Color']

                mix_adesivo.location = (-300, 300)
                input_fac_ad.default_value = 0.8  
                
                links.new(tex_node.outputs['Color'], input_a_ad)
                fator_escuro_cmyk = (0.30, 0.30, 0.30, 0.5)
                input_b_ad.default_value = fator_escuro_cmyk
                links.new(saida_mix_ad, bsdf.inputs[pino_cor])
            else:
                if preenchimento_val != 'Nenhum':
                    bsdf.inputs[pino_cor].default_value = cor_svg
            
            roughness_final = regra['roughness']
            if usar_verniz and tipo_material == 'MDF':
                roughness_final = 0.03

            if 'Roughness' in bsdf.inputs: 
                bsdf.inputs['Roughness'].default_value = roughness_final

            if tipo_material != 'ACRILICO':
                if 'Transmission Weight' in bsdf.inputs: 
                    bsdf.inputs['Transmission Weight'].default_value = regra.get('transmission', 0.0)
                elif 'Transmission' in bsdf.inputs: 
                    bsdf.inputs['Transmission'].default_value = regra.get('transmission', 0.0)
                if 'IOR' in bsdf.inputs and 'ior' in regra:
                    bsdf.inputs['IOR'].default_value = regra['ior']

            # Guarda o material configurado na memória cache
            materiais_criados[chave_material] = mat

        # Atribui o material (único ou reusado) ao objeto
        obj.data.materials.append(mat)
        bpy.context.view_layer.update()

    if os.path.exists(caminho_temp): os.remove(caminho_temp)

<<<<<<< HEAD
    # --- VERIFICAÇÃO DE RASTREIO E SUPORTE NA BASE ---
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    def esta_apoiado_na_base(obj_name):
        atual = obj_name
        visitados = set() 
        while atual and atual not in visitados:
            visitados.add(atual)
            for item in elementos_mapeados:
                try:
                    if item['obj'] and item['obj'].name == atual:
                        t_mat = item['tipo_material']
                        if t_mat in ['BASE', 'BASE_FINA']: 
                            return True 
                        elif t_mat in ['MDF']: 
                            return False 
                except (ReferenceError, AttributeError):
                    continue
            atual = suporte_dos_objetos.get(atual)
        return False

<<<<<<< HEAD
    # --- SELEÇÃO DAS PEÇAS QUE DEVEM ROTACIONAR DA HORIZONTAL PARA A VERTICAL ---
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    pecas_corpo = []
    status_rotacao = {}

    for item in elementos_mapeados:
        try:
            obj = item['obj']
            if not obj or obj.name not in bpy.data.objects:
                continue

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
                    except ReferenceError:
                        continue

            if t_mat in ['BASE', 'BASE_FINA']: 
                deve_rotacionar = False  
            elif t_mat in ['ACRILICO', 'ADESIVO', 'RESINA_AREA']:
                if apoiado_direto_na_base or esta_apoiado_na_base(nome_obj):
                    deve_rotacionar = False
                elif abaixo and abaixo in status_rotacao and not status_rotacao[abaixo]:
                    deve_rotacionar = False
                else:
                    deve_rotacionar = True
            else:
                if abaixo and abaixo in status_rotacao and not status_rotacao[abaixo]:
                    deve_rotacionar = True

            status_rotacao[nome_obj] = deve_rotacionar

            if deve_rotacionar: 
                pecas_corpo.append(obj)
        except (ReferenceError, AttributeError):
            pass

    # --- APLICA A ROTAÇÃO DE 90 GRAUS NO CORPO DO TROFÉU ---
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

<<<<<<< HEAD
    # --- PROCESSAMENTO DA RESINA COMO ÚLTIMA ETAPA (SOBRE O TROFÉU JÁ MONTADO E ROTACIONADO) ---
=======
    # --- PROCESSAMENTO DA RESINA COMO ÚLTIMA ETAPA ---
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    dados_resina_pendente = next((i for i in elementos_mapeados if i['tipo_material'] == 'RESINA_AREA'), None)

    if dados_resina_pendente:
        obj_marcado_svg = dados_resina_pendente['obj']
        
        if obj_marcado_svg and obj_marcado_svg.name in bpy.data.objects:
            bpy.context.view_layer.update()
            
<<<<<<< HEAD
            # Identifica se a guia do SVG passou pela rotação do MDF
            eh_mdf_rotacionado = 'matriz_final' in locals() and obj_marcado_svg in pecas_corpo
            
            # Cantos da caixa delimitadora no mundo 3D
=======
            eh_mdf_rotacionado = 'matriz_final' in locals() and obj_marcado_svg in pecas_corpo
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            cantos_guia = [obj_marcado_svg.matrix_world @ mathutils.Vector(v) for v in obj_marcado_svg.bound_box]
            
            xs_guia = [v.x for v in cantos_guia]
            ys_guia = [v.y for v in cantos_guia]
            zs_guia = [v.z for v in cantos_guia]
            
            largura_svg = abs(max(xs_guia) - min(xs_guia))
            
<<<<<<< HEAD
            # 1. Ajuste das dimensões dependendo da orientação (Em pé vs Deitado)
            if eh_mdf_rotacionado:
                # Se rotacionou no MDF, a altura do plano passa a ser o eixo Z
                altura_svg = abs(max(zs_guia) - min(zs_guia))
                centro_x = (max(xs_guia) + min(xs_guia)) / 2.0
                centro_y = (max(ys_guia) + min(ys_guia)) / 2.0  # Face frontal do MDF
                centro_z = (max(zs_guia) + min(zs_guia)) / 2.0
            else:
                # Se está na Base (plana), a altura do plano é o eixo Y
                altura_svg = abs(max(ys_guia) - min(ys_guia))
                centro_x = (max(xs_guia) + min(xs_guia)) / 2.0
                centro_y = (max(ys_guia) + min(ys_guia)) / 2.0
                centro_z = max(zs_guia)  # Topo da base

            # 2. Importa o arquivo 3D de resina
=======
            if eh_mdf_rotacionado:
                altura_svg = abs(max(zs_guia) - min(zs_guia))
                centro_x = (max(xs_guia) + min(xs_guia)) / 2.0
                centro_y = (max(ys_guia) + min(ys_guia)) / 2.0
                centro_z = (max(zs_guia) + min(zs_guia)) / 2.0
            else:
                altura_svg = abs(max(ys_guia) - min(ys_guia))
                centro_x = (max(xs_guia) + min(xs_guia)) / 2.0
                centro_y = (max(ys_guia) + min(ys_guia)) / 2.0
                centro_z = max(zs_guia)

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            if caminho_modelo_resina and os.path.exists(caminho_modelo_resina):
                extensao = os.path.splitext(caminho_modelo_resina)[1].lower()
                objs_antes_import = set(bpy.context.scene.objects)
                
                try:
                    if extensao in ['.obj', '.wavefront']:
                        window = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
                        screen = window.screen if window else None
                        area = next((a for a in screen.areas if a.type == 'VIEW_3D'), None) if screen else None

                        if window and area:
                            with bpy.context.temp_override(window=window, area=area):
                                bpy.ops.wm.obj_import(filepath=caminho_modelo_resina)
                        else:
                            bpy.ops.wm.obj_import(filepath=caminho_modelo_resina)

                    elif extensao == '.fbx':
                        try:
                            bpy.ops.import_scene.fbx(filepath=caminho_modelo_resina, use_custom_props=False)
                        except Exception as err_fbx:
                            print(f"⚠️ AVISO: FBX importado com ressalvas: {err_fbx}", flush=True)

                    elif extensao == '.stl':
                        bpy.ops.wm.stl_import(filepath=caminho_modelo_resina)

                    elif extensao == '.blend':
                        with bpy.data.libraries.load(caminho_modelo_resina, link=False) as (data_from, data_to):
                            data_to.objects = data_from.objects
                        for obj_carregado in data_to.objects:
                            if obj_carregado is not None:
                                bpy.context.scene.collection.objects.link(obj_carregado)
                except Exception as e_import:
                    print(f"❌ Erro ao importar modelo de resina: {e_import}", flush=True)

                novos_objs = list(set(bpy.context.scene.objects) - objs_antes_import)
                malhas_resina = [o for o in novos_objs if o.type == 'MESH']
                
                if malhas_resina:
                    resina_3d_obj = malhas_resina[0]
                    
<<<<<<< HEAD
                    # --- APLICAÇÃO DA COR DE PREENCHIMENTO DO SVG NA RESINA ---
                    preenchimento_val = dados_resina_pendente['dados'].get('preenchimento', 'Nenhum')
                    
                    if preenchimento_val != 'Nenhum':
                        cor_rgba = hex_para_rgba(preenchimento_val)
                        
                        # Limpa materiais antigos do modelo 3D importado
                        resina_3d_obj.data.materials.clear()
                        
                        # Cria o novo material usando o sistema de nós
                        nome_mat_resina = f"Mat_Resina_{dados_resina_pendente['nome_base']}"
                        mat_resina = bpy.data.materials.new(name=nome_mat_resina)
                        mat_resina.use_nodes = True
                        
                        nodes = mat_resina.node_tree.nodes
                        bsdf = nodes.get("Principled BSDF")
                        
                        if bsdf:
                            # Define a cor base vinda do SVG
                            if 'Base Color' in bsdf.inputs:
                                bsdf.inputs['Base Color'].default_value = cor_rgba
                            
                            # Ajuste de acabamento do material da resina (Lisa/Semi-brilhante)
                            if 'Roughness' in bsdf.inputs:
                                bsdf.inputs['Roughness'].default_value = 0.1
                        
                        resina_3d_obj.data.materials.append(mat_resina)
                    
                    # --- GARANTE VISIBILIDADE E ATIVAÇÃO ---
=======
                    # --- APLICAÇÃO DA COR, IOR E PROPRIEDADES DO SVG NA RESINA ---
                    preenchimento_val = dados_resina_pendente['dados'].get('preenchimento', 'Nenhum')
                    regra_resina = dados_resina_pendente['regra']
                    
                    # Limpa materiais genéricos/antigos do arquivo importado
                    resina_3d_obj.data.materials.clear()
                    
                    nome_mat_resina = f"Mat_Resina_{dados_resina_pendente['nome_base']}"
                    mat_resina = bpy.data.materials.new(name=nome_mat_resina)
                    mat_resina.use_nodes = True
                    
                    nodes = mat_resina.node_tree.nodes
                    bsdf = nodes.get("Principled BSDF")
                    
                    if bsdf:
                        # 1. Aplica a cor de preenchimento se existir
                        if preenchimento_val != 'Nenhum':
                            cor_rgba = hex_para_rgba(preenchimento_val)
                            if 'Base Color' in bsdf.inputs:
                                bsdf.inputs['Base Color'].default_value = cor_rgba
                        
                        # 2. Aplica a Rugosidade (Roughness) definida na regra
                        if 'Roughness' in bsdf.inputs:
                            bsdf.inputs['Roughness'].default_value = regra_resina.get('roughness', 0.1)
                            
                        # 3. Aplica a Transmissão / Transparência (Transmission)
                        if 'Transmission Weight' in bsdf.inputs:
                            bsdf.inputs['Transmission Weight'].default_value = regra_resina.get('transmission', 0.0)
                        elif 'Transmission' in bsdf.inputs:
                            bsdf.inputs['Transmission'].default_value = regra_resina.get('transmission', 0.0)
                            
                        # 4. Aplica o IOR (Índice de Refração)
                        if 'IOR' in bsdf.inputs and 'ior' in regra_resina:
                            bsdf.inputs['IOR'].default_value = regra_resina['ior']
                    
                    resina_3d_obj.data.materials.append(mat_resina)

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    resina_3d_obj.hide_set(False)
                    resina_3d_obj.hide_viewport = False
                    resina_3d_obj.hide_render = False
                    
                    bpy.ops.object.select_all(action='DESELECT')
                    resina_3d_obj.select_set(True)
                    bpy.context.view_layer.objects.active = resina_3d_obj
                    
<<<<<<< HEAD
                    # Centraliza o pivô na geometria real
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                    bpy.context.view_layer.update()
                    
                    # 3. Aplica rotação de 90° no X APENAS se estiver no MDF
=======
                    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
                    bpy.context.view_layer.update()
                    
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    if eh_mdf_rotacionado:
                        resina_3d_obj.rotation_euler.x += math.radians(90)
                        bpy.context.view_layer.update()

<<<<<<< HEAD
                    # 4. Medição das dimensões reais da peça 3D importada
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    cantos_obj = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
                    largura_obj = abs(max(v.x for v in cantos_obj) - min(v.x for v in cantos_obj))
                    
                    if eh_mdf_rotacionado:
                        altura_obj = abs(max(v.z for v in cantos_obj) - min(v.z for v in cantos_obj))
                    else:
                        altura_obj = abs(max(v.y for v in cantos_obj) - min(v.y for v in cantos_obj))

<<<<<<< HEAD
                    # 5. Rotação em Z se a maior dimensão do modelo não bater com a área do SVG
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    svg_eh_horizontal = largura_svg >= altura_svg
                    obj_eh_horizontal = largura_obj >= altura_obj
                    
                    if svg_eh_horizontal != obj_eh_horizontal:
                        resina_3d_obj.rotation_euler.z += math.radians(90)
                        bpy.context.view_layer.update()
                        
<<<<<<< HEAD
                        # Recalcula dimensões do objeto após giro em Z
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                        cantos_obj = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
                        largura_obj = abs(max(v.x for v in cantos_obj) - min(v.x for v in cantos_obj))
                        if eh_mdf_rotacionado:
                            altura_obj = abs(max(v.z for v in cantos_obj) - min(v.z for v in cantos_obj))
                        else:
                            altura_obj = abs(max(v.y for v in cantos_obj) - min(v.y for v in cantos_obj))

<<<<<<< HEAD
                    # 6. Escala Proporcional Idêntica à da Base
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    if largura_obj > 0.0001 and altura_obj > 0.0001 and largura_svg > 0.0001 and altura_svg > 0.0001:
                        fator_x = largura_svg / largura_obj
                        fator_y = altura_svg / altura_obj
                        escala_proporcional = min(fator_x, fator_y)
                        
                        if escala_proporcional > 0:
                            resina_3d_obj.scale = (
                                resina_3d_obj.scale.x * escala_proporcional,
                                resina_3d_obj.scale.y * escala_proporcional,
                                resina_3d_obj.scale.z * escala_proporcional
                            )
                        bpy.context.view_layer.update()

<<<<<<< HEAD
                    # 7. Posicionamento e Encaixe Final
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                    cantos_finais = [resina_3d_obj.matrix_world @ mathutils.Vector(v) for v in resina_3d_obj.bound_box]
                    centro_x_res = (max(v.x for v in cantos_finais) + min(v.x for v in cantos_finais)) / 2.0
                    
                    if eh_mdf_rotacionado:
                        centro_z_res = (max(v.z for v in cantos_finais) + min(v.z for v in cantos_finais)) / 2.0
<<<<<<< HEAD
                        
                        # Usa o Y mínimo da peça para encostar na face frontal (menor Y do MDF na visão da câmera)
                        max_y_res = max(v.y for v in cantos_finais)
                        min_y_res = min(v.y for v in cantos_finais)
                        
                        # Alinha no centro X e Z da marcação
                        resina_3d_obj.location.x += (centro_x - centro_x_res)
                        resina_3d_obj.location.z += (centro_z - centro_z_res)
                        
                        # DESLOCAMENTO PARA A FACE FRONTAL:
                        # Reposiciona na frente do Y mínimo da marcação (visível para a câmera)
                        min_y_guia_mdf = min(ys_guia)
                        resina_3d_obj.location.y += (min_y_guia_mdf - max_y_res) - 0.001
                        
                    else:
                        # Se está na Base (plana)
=======
                        max_y_res = max(v.y for v in cantos_finais)
                        
                        resina_3d_obj.location.x += (centro_x - centro_x_res)
                        resina_3d_obj.location.z += (centro_z - centro_z_res)
                        
                        min_y_guia_mdf = min(ys_guia)
                        resina_3d_obj.location.y += (min_y_guia_mdf - max_y_res) - 0.001
                    else:
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
                        centro_y_res = (max(v.y for v in cantos_finais) + min(v.y for v in cantos_finais)) / 2.0
                        min_z_res = min(v.z for v in cantos_finais)
                        
                        resina_3d_obj.location.x += (centro_x - centro_x_res)
                        resina_3d_obj.location.y += (centro_y - centro_y_res)
                        resina_3d_obj.location.z += (max(zs_guia) - min_z_res) + 0.001

<<<<<<< HEAD
            # 8. Remoção segura da guia 2D
=======
                    objetos_importados.append(resina_3d_obj)

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            try:
                if obj_marcado_svg and obj_marcado_svg.name in bpy.data.objects:
                    bpy.data.objects.remove(obj_marcado_svg, do_unlink=True)
            except (ReferenceError, KeyError):
                pass

<<<<<<< HEAD
       # --- CONFIGURAÇÃO DE CÂMERAS E ENQUADRAMENTO AUTOMÁTICO ---
    # Filtra apenas objetos válidos ainda existentes na cena do Blender
    # --- CONFIGURAÇÃO DE CÂMERAS E ENQUADRAMENTO AUTOMÁTICO ---
    # Filtra apenas objetos cuja referência em memória ainda é válida no Blender
=======
    # --- CONFIGURAÇÃO DE CÂMERAS E ENQUADRAMENTO AUTOMÁTICO ---
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    objetos_validos_cena = []
    for obj in objetos_importados:
        try:
            if obj and obj.name in bpy.data.objects:
                objetos_validos_cena.append(obj)
        except (ReferenceError, RuntimeError):
            continue

    if objetos_validos_cena:
        bpy.context.view_layer.update()
        render = bpy.context.scene.render
        render.resolution_x = 1080
        render.resolution_y = 1350
        aspect_ratio = render.resolution_x / render.resolution_y
        
        # Inicialização explícita das coordenadas de enquadramento
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

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

        if min_x != float('inf') and max_z != float('-inf'):
            alvo_centro = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
            tamanho_x = max_x - min_x
            tamanho_y = max_y - min_y
            tamanho_z = max_z - min_z
            tamanho_maximo = max(tamanho_x, tamanho_y, tamanho_z)

<<<<<<< HEAD
            # Ajusta posição das luzes da cena em relação ao novo centro do troféu
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            for obj_cena in bpy.context.scene.objects:
                if obj_cena.type == 'LIGHT':
                    direcao_luz = (obj_cena.location - alvo_centro).normalized()
                    distancia_luz = max(tamanho_maximo * 2.0, 0.5)
                    obj_cena.location = alvo_centro + (direcao_luz * distancia_luz)

<<<<<<< HEAD
            # Leitura do FOV e cálculo de distância focal
=======
>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
            dummy_cam_data = bpy.data.cameras.new("temp_cam")
            dummy_cam_obj = bpy.data.objects.new("temp_cam_obj", dummy_cam_data)
            fov = dummy_cam_data.angle
            bpy.data.objects.remove(dummy_cam_obj)
            bpy.data.cameras.remove(dummy_cam_data)

            tamanho_real = max(tamanho_z, tamanho_x / aspect_ratio) if aspect_ratio > 1 else max(tamanho_x, tamanho_z * aspect_ratio)
            distancia_base = (tamanho_real / 2.0) / math.tan(fov / 2.0) * 1.5

            ponto_focal_alvo = alvo_centro.copy()
            ponto_focal_alvo.z += tamanho_z * 0.07  
            
            altura_camera = alvo_centro.z + (tamanho_z * 0.4)  
            pos_cam_principal = mathutils.Vector((alvo_centro.x, min_y - distancia_base, altura_camera))
            
            cam_principal = bpy.data.objects.get("Camera_Principal")
            if not cam_principal:
                cam_data = bpy.data.cameras.new(name="Camera_Principal")
                cam_principal = bpy.data.objects.new("Camera_Principal", cam_data)
                bpy.context.scene.collection.objects.link(cam_principal)
            
            cam_principal.data.type = 'PERSP'
            cam_principal.location = pos_cam_principal
            direcao_principal = ponto_focal_alvo - cam_principal.location
            cam_principal.rotation_euler = direcao_principal.to_track_quat('-Z', 'Y').to_euler()

            angulo_diag = math.radians(35) 
            dist_lateral = distancia_base * 1.1
            
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
<<<<<<< HEAD

            criar_e_apontar_camera("Camera_Esquerda", mathutils.Vector((alvo_centro.x - (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)), ponto_focal_alvo)
            criar_e_apontar_camera("Camera_Direita", mathutils.Vector((alvo_centro.x + (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)), ponto_focal_alvo)
            
            bpy.context.scene.camera = cam_principal
=======

            criar_e_apontar_camera("Camera_Esquerda", mathutils.Vector((alvo_centro.x - (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)), ponto_focal_alvo)
            criar_e_apontar_camera("Camera_Direita", mathutils.Vector((alvo_centro.x + (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), altura_camera)), ponto_focal_alvo)
            
            bpy.context.scene.camera = cam_principal

>>>>>>> b69320dcb4abc697699275a67d3870eaf2add586
    # --- EXECUÇÃO DO RENDER VIA CYCLES ---
    if renderizar and pasta_saida_renders:
        pasta_dest = pasta_saida_renders
        if not os.path.exists(pasta_dest):
            os.makedirs(pasta_dest)
        
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        
        try:
            cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
            cycles_prefs.compute_device_type = 'NONE'
            scene.cycles.device = 'CPU'
        except Exception:
            pass
            
        total_samples = int(cycles_samples)
        scene.cycles.samples = total_samples
        scene.cycles.use_denoising = True

        cameras = [
            ("Camera_Principal", bpy.data.objects.get("Camera_Principal")),
            ("Camera_Esquerda", bpy.data.objects.get("Camera_Esquerda")),
            ("Camera_Direita", bpy.data.objects.get("Camera_Direita"))
        ]
        cameras_validas = [(nome, obj) for nome, obj in cameras if obj]

        for idx_cam, (nome_cam, cam) in enumerate(cameras_validas):
            scene.camera = cam
            caminho_arquivo_img = os.path.join(pasta_dest, f"{nome_cam}.png")
            scene.render.filepath = caminho_arquivo_img
            
            print(f">>> Renderizando câmera: {nome_cam} via Cycles...", flush=True)
            
            import time
            parar_thread = threading.Event()

            def atualizar_progresso_fluido():
                atual = 0
                limite_simulado = max(1, total_samples - 2)
                while not parar_thread.is_set() and atual < limite_simulado:
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
    else:
        print(">>> Modo interativo ativo: O Blender permaneceu aberto com o troféu montado.", flush=True)

        
if __name__ == "__main__":
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
        caminho_svg = argv[0] if len(argv) > 0 else ""
        pasta_saida = argv[1] if len(argv) > 1 else ""
        caminho_blend = argv[2] if len(argv) > 2 else ""
        
        renderizar_automaticamente = True
        if len(argv) > 3:
            renderizar_automaticamente = argv[3].lower() == 'true'
            
        usar_textura = True
        if len(argv) > 4:
            usar_textura = argv[4].lower() == 'true'
            
        cycles_samples = 128
        if len(argv) > 5:
            try:
                cycles_samples = int(argv[5])
            except:
                cycles_samples = 128
        usar_verniz = False
        if len(argv) > 6:
            usar_verniz = argv[6].lower() == 'true'
            
        caminho_modelo_resina = ""
        if len(argv) > 7:
            caminho_modelo_resina = argv[7]
            
        processar_svg_no_blender(caminho_svg, pasta_saida, caminho_blend, renderizar_automaticamente, usar_textura, cycles_samples, usar_verniz, caminho_modelo_resina)