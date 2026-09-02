import bpy
import xml.etree.ElementTree as ET
import re
import os
import mathutils 
import math 
import sys
import shutil

# --- REGRAS DE MATERIAIS AGRUPADOS POR TIPO ---
REGRAS_MATERIAIS = {    
    # ACRÍLICOS (Qualquer cor com tipo 'ACRILICO' vai herdar estas propriedades)
    '#ed3237': { 'tipo': 'ACRILICO', 'nome_material': 'acrilico_padrão', 'extrusao': 0.001, 'roughness': 0.00, 'transmission': 1.0, 'ior': 1.49 },
    '#fff212': { 'tipo': 'ACRILICO', 'nome_material': 'Acrilico_transparente', 'extrusao': 0.001, 'roughness': 0.01, 'transmission': 1.0, 'ior': 2 },
        
    
    # MDFs (Qualquer variação de MDF)
    '#fefefe': { 'tipo': 'MDF', 'nome_material': 'MDF_3mm', 'extrusao': 0.003, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#e6e7e8': { 'tipo': 'MDF', 'nome_material': 'MDF_6mm', 'extrusao': 0.006, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
    '#373435': { 'tipo': 'MDF', 'nome_material': 'PLOTTER', 'extrusao': 0.001, 'roughness': 0.08, 'transmission': 0.2, 'ior': 1.15},
                
    # BASES
    "#f58634": { 'tipo': 'BASE', 'nome_material': 'Base_3MM', 'extrusao': 0.003, 'roughness': 0.2, 'transmission': 0.0, 'ior': 1.15 },
    "#3e4095": { 'tipo': 'BASE', 'nome_material': 'Base_6MM', 'extrusao': 0.01, 'roughness': 0.2, 'transmission': 0.0, 'ior': 1.15},
    "#f7adaf": { 'tipo': 'BASE', 'nome_material': 'Base_9MM', 'extrusao': 0.015, 'roughness': 0.2, 'transmission': 0.0, 'ior': 1.15 },
    "#84716b": { 'tipo': 'BASE', 'nome_material': 'Base_9MM', 'extrusao': 0.02, 'roughness': 0.2, 'transmission': 0.0, 'ior': 1.115},
    
    # ADESIVOS
    '#ec268f': { 'tipo': 'ADESIVO', 'nome_material': 'Adesivo_Padrao', 'extrusao': 0.0001, 'roughness': 0.002, 'transmission': 0.5, 'ior': 1.3 }
}

def hex_para_rgba(hex_color, alpha=1.0):
    if not hex_color or not hex_color.startswith('#'): return (1.0, 1.0, 1.0, alpha)
    hex_color = hex_color.lstrip('#').lower()
    r, g, b = int(hex_color[0:2], 16)/255.0, int(hex_color[2:4], 16)/255.0, int(hex_color[4:6], 16)/255.0
    fator_cmyk = 0.75 
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

def processar_svg_no_blender(caminho_svg, pasta_saida_renders, caminho_blend="", renderizar=True, usar_textura=True, cycles_samples=128):
    # 1. Carrega o estúdio base se fornecido
    if caminho_blend and os.path.exists(caminho_blend):
        print(f">>> Carregando estúdio base: {caminho_blend}")
        bpy.ops.wm.open_mainfile(filepath=caminho_blend)

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
    
    # Importação limpa do SVG
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.import_curve.svg(filepath=caminho_temp)
    
    objetos_importados = list(set(bpy.context.scene.objects) - objetos_antes)
    
    # Vinculação rigorosa à cena principal
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

    # Conversão direta via dados (Nível de API)
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

    # --- FUNÇÃO AUXILIAR PARA LER O ID NUMÉRICO DO SVG ---
    def obter_id_numerico(obj):
        match = re.search(r'trofeu_shape_(\d+)', obj.name)
        return int(match.group(1)) if match else 9999

    # --- MAPEAMENTO RIGOROSO NA ORDEM EXATA DO SVG (Sem blocos fixos) ---
    elementos_mapeados = []
    
    for idx, obj in enumerate(objetos_importados):
        num_id = obter_id_numerico(obj)
        nome_base = f"trofeu_shape_{num_id}" if num_id != 9999 else f"trofeu_shape_{idx+1}"
        
        dados = dados_extraidos.get(nome_base, {'contorno': '#fefefe', 'preenchimento': 'Nenhum'})
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

    # --- ORDENAÇÃO POR CAMADAS DO SVG ---
    # As bases vão primeiro para servirem de fundação, e o restante das peças segue a ordem de camadas do SVG.
    elementos_mapeados.sort(key=lambda x: (0 if x['eh_base'] else 1, x['indice_svg']))

    idx_imagem_global = 0
    suporte_dos_objetos = {}

    # --- LOOP DE PROCESSAMENTO E MONTAGEM ORDENADA ---
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

        # Modificador de Extrusão com tratamento de segurança blindado
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
        mat = bpy.data.materials.new(name=f"Mat_{regra['nome_material']}_{nome_base}")
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

        preenchimento_val = dados.get('preenchimento', 'Nenhum')
        cor_svg = hex_para_rgba(preenchimento_val) if preenchimento_val != 'Nenhum' else (0.8, 0.6, 0.4, 1.0)

        # Aplicação rigorosa de imagem EXCLUSIVAMENTE para materiais do tipo ADESIVO
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
            tex_node.location = (-300, 300)
            links.new(tex_node.outputs['Color'], bsdf.inputs[pino_cor])
            
        elif 'textura' in regra and regra['textura'] and usar_textura:
            caminho_textura = os.path.join(pasta_script_atual, "textura", regra['textura'])
            
            if os.path.exists(caminho_textura):
                tex_node = nodes.new('ShaderNodeTexImage')
                tex_node.location = (-600, 300)
                tex_node.projection = 'BOX' 
                tex_node.projection_blend = 0.15 
                
                tex_coord = nodes.new('ShaderNodeTexCoord')
                tex_coord.location = (-1000, 300)
                mapping_node = nodes.new('ShaderNodeMapping')
                mapping_node.location = (-800, 300)
                escala = regra.get('escala_textura', 1.0)
                mapping_node.inputs['Scale'].default_value = (escala, escala, escala)

                links.new(tex_coord.outputs['Object'], mapping_node.inputs['Vector'])
                links.new(mapping_node.outputs['Vector'], tex_node.inputs['Vector'])
                
                img_nome_mdf = os.path.basename(caminho_textura)
                img_blender = bpy.data.images.get(img_nome_mdf)
                if not img_blender:
                    img_blender = bpy.data.images.load(filepath=caminho_textura)
                tex_node.image = img_blender

                if bpy.app.version >= (3, 4, 0):
                    mix_node = nodes.new('ShaderNodeMix')
                    mix_node.data_type = 'RGBA'
                    mix_node.blend_type = 'MULTIPLY'
                    input_fac = mix_node.inputs.get('Factor', mix_node.inputs[0])
                    input_a = mix_node.inputs.get('A', mix_node.inputs[6])
                    input_b = mix_node.inputs.get('B', mix_node.inputs[7])
                    saida_mix = mix_node.outputs.get('Result', mix_node.outputs[2])
                else:
                    mix_node = nodes.new('ShaderNodeMixRGB')
                    mix_node.blend_type = 'MULTIPLY'
                    input_fac = mix_node.inputs['Fac']
                    input_a = mix_node.inputs['Color1']
                    input_b = mix_node.inputs['Color2']
                    saida_mix = mix_node.outputs['Color']

                mix_node.location = (-300, 300)
                input_fac.default_value = 1.0
                links.new(tex_node.outputs['Color'], input_a)
                input_b.default_value = cor_svg
                links.new(saida_mix, bsdf.inputs[pino_cor])
            else:
                if preenchimento_val != 'Nenhum':
                    bsdf.inputs[pino_cor].default_value = cor_svg
        else:
            if preenchimento_val != 'Nenhum':
                bsdf.inputs[pino_cor].default_value = cor_svg

        if 'Roughness' in bsdf.inputs: 
            bsdf.inputs['Roughness'].default_value = regra['roughness']
        if tipo_material != 'ACRILICO':
            if 'Transmission Weight' in bsdf.inputs: 
                bsdf.inputs['Transmission Weight'].default_value = regra.get('transmission', 0.0)
            elif 'Transmission' in bsdf.inputs: 
                bsdf.inputs['Transmission'].default_value = regra.get('transmission', 0.0)
            if 'IOR' in bsdf.inputs and 'ior' in regra:
                bsdf.inputs['IOR'].default_value = regra['ior']

        obj.data.materials.append(mat)
        bpy.context.view_layer.update()
            
    if os.path.exists(caminho_temp): os.remove(caminho_temp)
    
    def esta_apoiado_na_base(obj_name):
        atual = obj_name
        visitados = set() 
        while atual and atual not in visitados:
            visitados.add(atual)
            for item in elementos_mapeados:
                if item['obj'].name == atual:
                    t_mat = item['tipo_material']
                    if t_mat in ['BASE', 'BASE_FINA']: return True 
                    elif t_mat in ['MDF', 'ACRILICO']: return False 
            atual = suporte_dos_objetos.get(atual)
        return False

    # --- FILTRO RIGOROSO DE ROTAÇÃO (As bases NUNCA rotacionam, apenas o corpo do troféu) ---
    pecas_corpo = []
    for item in elementos_mapeados:
        obj = item['obj']
        t_mat = item['tipo_material']
        try:
            if obj.name in bpy.data.objects:
                deve_rotacionar = True 
                if t_mat in ['BASE', 'BASE_FINA']: 
                    deve_rotacionar = False  # Base fica intacta no plano horizontal
                elif t_mat == 'ADESIVO' and esta_apoiado_na_base(obj.name): 
                    deve_rotacionar = False 
                
                if deve_rotacionar: 
                    pecas_corpo.append(obj)
        except ReferenceError: pass

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
            
    if objetos_importados:
        bpy.context.view_layer.update()
        render = bpy.context.scene.render
        render.resolution_x = 1080
        render.resolution_y = 1350
        aspect_ratio = render.resolution_x / render.resolution_y
        
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')

        for obj in objetos_importados:
            for v in obj.bound_box:
                coord = obj.matrix_world @ mathutils.Vector(v)
                min_x = min(min_x, coord.x)
                max_x = max(max_x, coord.x)
                min_y = min(min_y, coord.y)
                max_y = max(max_y, coord.y)
                min_z = min(min_z, coord.z)
                max_z = max(max_z, coord.z)

        alvo_centro = mathutils.Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
        tamanho_x = max_x - min_x
        tamanho_z = max_z - min_z

        def criar_e_apontar_camera(nome, local_vetor):
            cam_obj = bpy.data.objects.get(nome)
            if not cam_obj:
                cam_data = bpy.data.cameras.new(name=nome)
                cam_obj = bpy.data.objects.new(nome, cam_data)
                bpy.context.scene.collection.objects.link(cam_obj)
            cam_obj.data.type = 'PERSP'
            cam_obj.location = local_vetor
            direcao = alvo_centro - cam_obj.location
            cam_obj.rotation_euler = direcao.to_track_quat('-Z', 'Y').to_euler()
            return cam_obj

        dummy_cam_data = bpy.data.cameras.new("temp_cam")
        dummy_cam_obj = bpy.data.objects.new("temp_cam_obj", dummy_cam_data)
        fov = dummy_cam_data.angle
        bpy.data.objects.remove(dummy_cam_obj)
        bpy.data.cameras.remove(dummy_cam_data)

        tamanho_real = max(tamanho_z, tamanho_x / aspect_ratio) if aspect_ratio > 1 else max(tamanho_x, tamanho_z * aspect_ratio)
        distancia_base = (tamanho_real / 2.0) / math.tan(fov / 2.0) * 1.5

        criar_e_apontar_camera("Camera_Principal", mathutils.Vector((alvo_centro.x, min_y - distancia_base, alvo_centro.z)))
        
        angulo_diag = math.radians(35) 
        dist_lateral = distancia_base * 1.1
        criar_e_apontar_camera("Camera_Esquerda", mathutils.Vector((alvo_centro.x - (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), alvo_centro.z + (tamanho_z * 0.15))))
        criar_e_apontar_camera("Camera_Direita", mathutils.Vector((alvo_centro.x + (dist_lateral * math.sin(angulo_diag)), alvo_centro.y - (dist_lateral * math.cos(angulo_diag)), alvo_centro.z + (tamanho_z * 0.15))))
        
        bpy.context.scene.camera = bpy.data.objects.get("Camera_Principal")

    if renderizar and pasta_saida_renders:
        nome_trofeu = os.path.splitext(os.path.basename(caminho_svg))[0]
        pasta_dest = os.path.join(pasta_saida_renders, nome_trofeu)
        if os.path.exists(pasta_dest):
            shutil.rmtree(pasta_dest)
        os.makedirs(pasta_dest)
        
        # --- BLINDAGEM DO CYCLES PARA BACKGROUND ---
        scene = bpy.context.scene
        scene.render.engine = 'CYCLES'
        
        # Configura o Cycles para usar a CPU em modo background (Evita o travamento de contexto da GPU)
        try:
            cycles_prefs = bpy.context.preferences.addons['cycles'].preferences
            cycles_prefs.compute_device_type = 'NONE' # Força o uso seguro da CPU no subprocesso
            scene.cycles.device = 'CPU'
        except Exception:
            pass
            
        # Otimizações para renderização rápida e limpa em background
        scene.cycles.samples = int(cycles_samples) # Reduz o tempo de render mantendo alta qualidade
        scene.cycles.use_denoising = True

        cameras = [bpy.data.objects.get("Camera_Principal"), bpy.data.objects.get("Camera_Esquerda"), bpy.data.objects.get("Camera_Direita")]
        for cam in cameras:
            if cam:
                scene.camera = cam
                scene.render.filepath = os.path.join(pasta_dest, f"{cam.name}.png")
                print(f">>> Renderizando câmera: {cam.name} via Cycles...")
                bpy.ops.render.render(write_still=True)
                
        print(f"Renders salvos em: {pasta_dest}")
    else:
        print(">>> Modo interativo ativo: O Blender permaneceu aberto com o troféu montado.")

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
        processar_svg_no_blender(caminho_svg, pasta_saida, caminho_blend, renderizar_automaticamente, usar_textura, cycles_samples)