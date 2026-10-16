import os
import re
import json
import math
import subprocess
import threading
import textwrap
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from svgpathtools import parse_path
    HAS_SVGPATH = True
except ImportError:
    HAS_SVGPATH = False

CONFIG_FILE = "config.json"

# ==============================================================================
# DICIONÁRIO DE MATERIAIS PADRÃO
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

# ==============================================================================
# FUNÇÕES DE EXTRAÇÃO SVG E MAPEAMENTO DO CATÁLOGO
# ==============================================================================
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

    return {'tipo': 'OUTRO', 'nome_material': f'Cor_{cor_clean}'}

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
        return None

    try:
        tree = ET.parse(caminho_svg)
        root = tree.getroot()
    except Exception:
        return None

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

            if mat_info and mat_info['tipo'] in TIPOS_CORPO_EXCLUSIVO and not eh_pagina:
                if tag == 'path':
                    d = elem.attrib.get('d', '')
                    if HAS_SVGPATH:
                        try:
                            path_obj = parse_path(d)
                            for sp in path_obj.continuous_subpaths():
                                xmin, xmax, ymin, ymax = sp.bbox()
                                w_mm = (xmax - xmin) * fator_mm
                                h_mm = (ymax - ymin) * fator_mm
                                larg = min(w_mm, h_mm)
                                alt = max(w_mm, h_mm)
                                if larg > 30.0 and alt > 30.0:
                                    pecas_isoladas.append((larg, alt, mat_info['nome_material']))
                        except Exception:
                            pass
                    else:
                        sub_str = re.split(r'(?=[Mm])', d)
                        for sp in sub_str:
                            if not sp.strip(): continue
                            coords = [float(v) for v in re_coords.findall(sp)]
                            if len(coords) >= 4:
                                xs, ys = coords[0::2], coords[1::2]
                                w_mm = (max(xs) - min(xs)) * fator_mm
                                h_mm = (max(ys) - min(ys)) * fator_mm
                                larg, alt = min(w_mm, h_mm), max(w_mm, h_mm)
                                if larg > 30.0 and alt > 30.0:
                                    pecas_isoladas.append((larg, alt, mat_info['nome_material']))

                elif tag == 'rect':
                    rw = float(elem.attrib.get('width', 0))
                    rh = float(elem.attrib.get('height', 0))
                    if rw > 0 and rh > 0:
                        w_mm, h_mm = rw * fator_mm, rh * fator_mm
                        larg, alt = min(w_mm, h_mm), max(w_mm, h_mm)
                        if larg > 30.0 and alt > 30.0:
                            pecas_isoladas.append((larg, alt, mat_info['nome_material']))

    if pecas_isoladas:
        pecas_isoladas.sort(key=lambda p: p[1], reverse=True)
        larg_mm, alt_mm, nome_fundo = pecas_isoladas[0]
    else:
        larg_mm, alt_mm, nome_fundo = 0.0, 0.0, "N/A"

    return {
        'nome_arquivo': os.path.basename(caminho_svg),
        'materiais_qtd': materiais_qtd,
        'largura_mm': larg_mm,
        'altura_mm': alt_mm,
        'largura_cm': larg_mm / 10.0,
        'altura_cm': alt_mm / 10.0,
        'nome_fundo': nome_fundo
    }


def mapear_catalogo(caminho_catalogo):
    if not os.path.exists(caminho_catalogo):
        return None, "❌ Diretório do catálogo não foi encontrado."

    modalidades = {}
    try:
        itens_raiz = sorted(os.listdir(caminho_catalogo))
    except Exception as e:
        return None, f"❌ Erro ao acessar diretório: {e}"

    for item in itens_raiz:
        caminho_modalidade = os.path.join(caminho_catalogo, item)
        if os.path.isdir(caminho_modalidade):
            nome_modalidade = item.upper()
            pastas_prontas = []
            svg_count_total = 0

            try:
                modelos = sorted(os.listdir(caminho_modalidade))
                for modelo_cod in modelos:
                    caminho_modelo = os.path.join(caminho_modalidade, modelo_cod)
                    if os.path.isdir(caminho_modelo):
                        caminho_svg_dir = None
                        for sub in os.listdir(caminho_modelo):
                            if sub.upper() == "SVG" and os.path.isdir(os.path.join(caminho_modelo, sub)):
                                caminho_svg_dir = os.path.join(caminho_modelo, sub)
                                break
                        if caminho_svg_dir:
                            svgs = [f for f in os.listdir(caminho_svg_dir) if f.lower().endswith('.svg')]
                            qtd_svgs = len(svgs)
                            if qtd_svgs > 0:
                                svg_count_total += qtd_svgs
                                pastas_prontas.append(modelo_cod)
            except Exception:
                pass

            modalidades[nome_modalidade] = {
                'svg_count': svg_count_total,
                'pastas_prontas': pastas_prontas
            }

    return modalidades, "OK"


# ==============================================================================
# JANELAS DA INTERFACE
# ==============================================================================
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configurações do Sistema")
        self.geometry("580x520")
        self.configure(bg="#121824")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent_app = parent
        self.blender_path_var = tk.StringVar(value=parent.blender_path)
        self.resina_dir_var = tk.StringVar(value=parent.resina_dir)
        self.blend_dir_var = tk.StringVar(value=parent.blend_dir)
        self.catalogo_dir_var = tk.StringVar(value=parent.catalogo_dir)
        self.selected_blend_var = tk.StringVar(value=parent.selected_blend)
        self.cycles_samples_var = tk.StringVar(value=str(parent.cycles_samples))
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="⚙ Configurações e Diretórios", fg="#FFFFFF", bg="#121824", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 10))

        # Executável do Blender
        f_b = tk.Frame(self, bg="#121824")
        f_b.pack(fill="x", padx=20, pady=4)
        tk.Label(f_b, text="Executável do Blender (blender.exe):", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w")
        sub_b = tk.Frame(f_b, bg="#121824")
        sub_b.pack(fill="x")
        tk.Entry(sub_b, textvariable=self.blender_path_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid").pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))
        tk.Button(sub_b, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_blender).pack(side="right")

        # Diretório do Catálogo
        f_c = tk.Frame(self, bg="#121824")
        f_c.pack(fill="x", padx=20, pady=4)
        tk.Label(f_c, text="Pasta Raiz do Catálogo:", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w")
        sub_c = tk.Frame(f_c, bg="#121824")
        sub_c.pack(fill="x")
        tk.Entry(sub_c, textvariable=self.catalogo_dir_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid").pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))
        tk.Button(sub_c, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_catalogo_dir).pack(side="right")

        # Pasta de Modelos 3D (Resina)
        f_r = tk.Frame(self, bg="#121824")
        f_r.pack(fill="x", padx=20, pady=4)
        tk.Label(f_r, text="Pasta dos Modelos 3D (Resina):", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w")
        sub_r = tk.Frame(f_r, bg="#121824")
        sub_r.pack(fill="x")
        tk.Entry(sub_r, textvariable=self.resina_dir_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid").pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))
        tk.Button(sub_r, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_resina_dir).pack(side="right")

        # Pasta dos Arquivos .Blend
        f_d = tk.Frame(self, bg="#121824")
        f_d.pack(fill="x", padx=20, pady=4)
        tk.Label(f_d, text="Pasta dos Estúdios Base (.blend):", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w")
        sub_d = tk.Frame(f_d, bg="#121824")
        sub_d.pack(fill="x")
        tk.Entry(sub_d, textvariable=self.blend_dir_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid").pack(side="left", fill="x", expand=True, ipady=3, padx=(0, 8))
        tk.Button(sub_d, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_blend_dir).pack(side="right")

        # Dropdown Blend
        f_sel = tk.Frame(self, bg="#121824")
        f_sel.pack(fill="x", padx=20, pady=4)
        tk.Label(f_sel, text="Estúdio Base (.blend) Ativo:", fg="#38BDF8", bg="#121824", font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.blend_dropdown_menu = tk.OptionMenu(f_sel, self.selected_blend_var, "")
        self.blend_dropdown_menu.config(bg="#080C14", fg="#FFFFFF", activebackground="#1E2638", activeforeground="#FFFFFF", bd=1, relief="solid", highlightthickness=0)
        self.blend_dropdown_menu.pack(fill="x")
        self._atualizar_lista_blends()

        # Cycles Samples
        f_samp = tk.Frame(self, bg="#121824")
        f_samp.pack(fill="x", padx=20, pady=4)
        tk.Label(f_samp, text="Qtd de Samples do Cycles:", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w")
        tk.Entry(f_samp, textvariable=self.cycles_samples_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid", width=15).pack(anchor="w", ipady=3)

        tk.Button(self, text="Salvar Configurações", bg="#38BDF8", fg="#FFFFFF", bd=0, font=("Helvetica", 10, "bold"), pady=8, command=self._save_settings).pack(fill="x", padx=20, pady=(15, 0))

    def _select_blender(self):
        f = filedialog.askopenfilename(title="Selecione o executável do Blender", filetypes=[("Executável Blender", "blender.exe"), ("Todos", "*.*")])
        if f: self.blender_path_var.set(f)

    def _select_catalogo_dir(self):
        f = filedialog.askdirectory(title="Selecione a Pasta Raiz do Catálogo")
        if f: self.catalogo_dir_var.set(f)

    def _select_resina_dir(self):
        f = filedialog.askdirectory(title="Selecione a Pasta de Modelos 3D (Resina)")
        if f: self.resina_dir_var.set(f)

    def _select_blend_dir(self):
        f = filedialog.askdirectory(title="Selecione a Pasta contendo os arquivos .blend")
        if f:
            self.blend_dir_var.set(f)
            self._atualizar_lista_blends()

    def _atualizar_lista_blends(self):
        pasta = self.blend_dir_var.get()
        menu = self.blend_dropdown_menu["menu"]
        menu.delete(0, "end")
        arquivos_blend = [arq for arq in os.listdir(pasta) if arq.lower().endswith(".blend")] if pasta and os.path.exists(pasta) else []
        if arquivos_blend:
            for arq in arquivos_blend:
                menu.add_command(label=arq, command=lambda value=arq: self.selected_blend_var.set(value))
            if self.selected_blend_var.get() not in arquivos_blend:
                self.selected_blend_var.set(arquivos_blend[0])
        else:
            self.selected_blend_var.set("Nenhum arquivo .blend encontrado")
            menu.add_command(label="Nenhum arquivo .blend encontrado", command=lambda: None)

    def _save_settings(self):
        self.parent_app.blender_path = self.blender_path_var.get()
        self.parent_app.resina_dir = self.resina_dir_var.get()
        self.parent_app.blend_dir = self.blend_dir_var.get()
        self.parent_app.catalogo_dir = self.catalogo_dir_var.get()
        self.parent_app.selected_blend = self.selected_blend_var.get()
        try:
            self.parent_app.cycles_samples = int(self.cycles_samples_var.get())
        except ValueError:
            self.parent_app.cycles_samples = 128
        self.parent_app.salvar_configuracoes_disco()
        if hasattr(self.parent_app, "_atualizar_hud_resina"):
            self.parent_app._atualizar_hud_resina()
        messagebox.showinfo("Sucesso", "Configurações salvas permanentemente!", parent=self)
        self.destroy()


class VectorConvertProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VectorConvert Pro")
        self.geometry("1150x780")
        self.configure(bg="#0B0F17")

        # Configurações Padrão
        self.blender_path = r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
        self.output_path = os.path.join(os.getcwd(), "imagens")
        self.resina_dir = os.path.join(os.getcwd(), "resina_models")
        self.blend_dir = os.getcwd()
        self.catalogo_dir = r"F:\Backup Aroni 29-05-2021\Publico\2026\CATALOGO"
        self.selected_blend = ""
        self.svg_selecionado = ""
        self.cycles_samples = 128

        self.carregar_configuracoes_disco()

        if not os.path.exists(self.resina_dir):
            os.makedirs(self.resina_dir)

        self.render_auto_var = tk.BooleanVar(value=True)
        self.usar_textura_var = tk.BooleanVar(value=True)
        self.usar_verniz_var = tk.BooleanVar(value=False)
        self.modelo_resina_selecionado = tk.StringVar(value="Nenhum")

        self.sidebar_buttons = {}
        self.screens = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_navbar()
        self._build_sidebar()
        
        self.main_container = tk.Frame(self, bg="#0B0F17")
        self.main_container.grid(row=1, column=1, sticky="nsew", padx=30, pady=15)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self._build_upload_screen()
        self._build_processing_screen()
        self._build_download_screen()
        self._build_catalogo_screen()

        self._build_footer()
        self._show_screen("upload")

    def carregar_configuracoes_disco(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    self.blender_path = dados.get("blender_path", self.blender_path)
                    self.resina_dir = dados.get("resina_dir", self.resina_dir)
                    self.blend_dir = dados.get("blend_dir", self.blend_dir)
                    self.catalogo_dir = dados.get("catalogo_dir", self.catalogo_dir)
                    self.selected_blend = dados.get("selected_blend", self.selected_blend)
                    self.cycles_samples = int(dados.get("cycles_samples", self.cycles_samples))
            except Exception as e:
                print(f"Erro ao carregar configurações: {e}")

    def salvar_configuracoes_disco(self):
        dados = {
            "blender_path": self.blender_path,
            "resina_dir": self.resina_dir,
            "blend_dir": self.blend_dir,
            "catalogo_dir": self.catalogo_dir,
            "selected_blend": self.selected_blend,
            "cycles_samples": self.cycles_samples
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações no disco: {e}")

    def _build_navbar(self):
        navbar = tk.Frame(self, bg="#0F141C", height=50, padx=20, pady=10)
        navbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        tk.Label(navbar, text="VectorConvert Pro", fg="#4C9EEB", bg="#0F141C", font=("Helvetica", 14, "bold")).pack(side="left", padx=10)
        
        right_icons_frame = tk.Frame(navbar, bg="#0F141C")
        right_icons_frame.pack(side="right", padx=10)
        tk.Button(right_icons_frame, text="⚙", fg="#A0AEC0", bg="#0F141C", bd=0, font=("Helvetica", 12), command=lambda: SettingsWindow(self)).pack(side="left", padx=8)

    def _build_sidebar(self):
        sidebar = tk.Frame(self, bg="#121824", width=220)
        sidebar.grid(row=1, column=0, sticky="nsew")
        sidebar.pack_propagate(False)

        header_frame = tk.Frame(sidebar, bg="#121824", pady=20, padx=15)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="SVG Converter", fg="#FFFFFF", bg="#121824", font=("Helvetica", 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(header_frame, text="HIGH PRECISION TOOL", fg="#4A5568", bg="#121824", font=("Helvetica", 8, "bold"), anchor="w").pack(fill="x")
        tk.Frame(sidebar, bg="#1A202C", height=1).pack(fill="x", pady=5)

        menu_items = {
            "upload": " Upload",
            "processing": " Processing",
            "download": " Download",
            "catalogo": " 📊 Catálogo"
        }
        for key, text in menu_items.items():
            btn = tk.Button(sidebar, text=text, fg="#A0AEC0", bg="#121824", bd=0, anchor="w", padx=20, pady=12, font=("Helvetica", 10), command=lambda k=key: self._show_screen(k))
            btn.pack(fill="x", pady=2)
            self.sidebar_buttons[key] = btn

    def _show_screen(self, screen_key):
        for key, btn in self.sidebar_buttons.items():
            if key == screen_key:
                btn.configure(bg="#1E2638", fg="#38BDF8", font=("Helvetica", 10, "bold"))
            else:
                btn.configure(bg="#121824", fg="#A0AEC0", font=("Helvetica", 10, "normal"))
        
        if screen_key == "catalogo":
            self._atualizar_relatorio_catalogo()

        self.screens[screen_key].tkraise()

    def _create_stepper(self, parent, active_step):
        stepper_frame = tk.Frame(parent, bg="#0B0F17")
        stepper_frame.pack(fill="x", pady=(5, 15))

        steps = [("1", "UPLOAD"), ("2", "PROCESSING"), ("3", "DOWNLOAD")]
        stepper_inner = tk.Frame(stepper_frame, bg="#0B0F17")
        stepper_inner.pack(anchor="center")

        for idx, (num, label) in enumerate(steps, start=1):
            step_item = tk.Frame(stepper_inner, bg="#0B0F17")
            step_item.pack(side="left", padx=20)
            completed = idx <= active_step
            circle_color = "#38BDF8" if completed else "#1E2638"
            text_color = "#FFFFFF" if completed else "#4A5568"
            symbol = "✓" if idx < active_step else num

            tk.Label(step_item, text=symbol, fg=text_color, bg=circle_color, width=3, height=1, font=("Helvetica", 10, "bold")).pack()
            tk.Label(step_item, text=label, fg=text_color, bg="#0B0F17", font=("Helvetica", 8, "bold")).pack(pady=(2, 0))

    def _atualizar_hud_resina(self):
        menu = self.menu_resina["menu"]
        menu.delete(0, "end")
        arquivos = [f for f in os.listdir(self.resina_dir) if f.lower().endswith(('.obj', '.fbx', '.stl', '.blend'))] if os.path.exists(self.resina_dir) else []
        if arquivos:
            menu.add_command(label="Nenhum (Ignorar Encaixe)", command=lambda: self.modelo_resina_selecionado.set("Nenhum"))
            for arq in arquivos:
                menu.add_command(label=arq, command=lambda v=arq: self.modelo_resina_selecionado.set(v))
            if self.modelo_resina_selecionado.get() not in arquivos:
                self.modelo_resina_selecionado.set(arquivos[0])
        else:
            self.modelo_resina_selecionado.set("Nenhum modelo 3D encontrado")
            menu.add_command(label="Nenhum modelo 3D encontrado", command=lambda: None)

    def _build_upload_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["upload"] = screen

        self._create_stepper(screen, active_step=1)
        
        main_frame = tk.Frame(screen, bg="#0B0F17")
        main_frame.pack(fill="both", expand=True)

        # Lado Esquerdo: Formulário de Upload e Opções
        card_left = tk.Frame(main_frame, bg="#121824", bd=1, relief="solid")
        card_left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(card_left, text="Upload e Parâmetros do SVG", fg="#FFFFFF", bg="#121824", font=("Helvetica", 12, "bold")).pack(pady=(15, 5))
        
        self.lbl_arquivo_selecionado = tk.Label(card_left, text="Nenhum arquivo selecionado", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9))
        self.lbl_arquivo_selecionado.pack(pady=2)

        btn_select = tk.Button(card_left, text="Selecionar Arquivo SVG", fg="#FFFFFF", bg="#1E2638", bd=0, padx=15, pady=8, font=("Helvetica", 9, "bold"), command=self._selecionar_svg)
        btn_select.pack(pady=10)

        chk_render = tk.Checkbutton(card_left, text="Renderizar automaticamente no Blender", variable=self.render_auto_var, fg="#A0AEC0", bg="#121824", selectcolor="#080C14", activebackground="#121824", font=("Helvetica", 9))
        chk_render.pack(pady=2, anchor="w", padx=20)

        chk_textura = tk.Checkbutton(card_left, text="Aplicar texturas (madeira no MDF)", variable=self.usar_textura_var, fg="#A0AEC0", bg="#121824", selectcolor="#080C14", activebackground="#121824", font=("Helvetica", 9))
        chk_textura.pack(pady=2, anchor="w", padx=20)

        chk_verniz = tk.Checkbutton(card_left, text="Aplicar Verniz na madeira", variable=self.usar_verniz_var, fg="#A0AEC0", bg="#121824", selectcolor="#080C14", activebackground="#121824", font=("Helvetica", 9))
        chk_verniz.pack(pady=2, anchor="w", padx=20)

        frame_resina = tk.Frame(card_left, bg="#121824")
        frame_resina.pack(fill="x", padx=20, pady=10)
        tk.Label(frame_resina, text="💎 Modelo 3D de Resina para Encaixe:", fg="#38BDF8", bg="#121824", font=("Helvetica", 9, "bold")).pack(anchor="w")
        self.menu_resina = tk.OptionMenu(frame_resina, self.modelo_resina_selecionado, "")
        self.menu_resina.config(bg="#080C14", fg="#FFFFFF", activebackground="#1E2638", bd=1, relief="solid", highlightthickness=0)
        self.menu_resina.pack(fill="x", pady=2)
        self._atualizar_hud_resina()

        # Botão Próximo para avançar
        btn_proximo = tk.Button(
            card_left, text="Próximo ➔", fg="#FFFFFF", bg="#38BDF8", bd=0, padx=20, pady=10, 
            font=("Helvetica", 10, "bold"), command=self._avancar_para_processamento
        )
        btn_proximo.pack(pady=(15, 10))

        # Lado Direito: Card de Análise Rápida do SVG
        card_right = tk.Frame(main_frame, bg="#121824", bd=1, relief="solid")
        card_right.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(card_right, text="📊 Análise Estrutural do SVG", fg="#38BDF8", bg="#121824", font=("Helvetica", 12, "bold")).pack(pady=(15, 5))
        
        self.txt_analise_svg = tk.Text(card_right, bg="#080C14", fg="#34D399", font=("Consolas", 9), bd=0, padx=10, pady=10)
        self.txt_analise_svg.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        self.txt_analise_svg.insert("1.0", "Aguardando seleção de arquivo SVG...")
        self.txt_analise_svg.configure(state="disabled")

    def _selecionar_svg(self):
        file_path = filedialog.askopenfilename(title="Selecionar SVG", filetypes=[("Arquivos SVG", "*.svg"), ("Todos", "*.*")])
        if file_path:
            self.svg_selecionado = file_path
            self.lbl_arquivo_selecionado.configure(text=os.path.basename(file_path), fg="#34D399")
            
            diretorio_svg = os.path.dirname(file_path)
            self.output_path = os.path.join(diretorio_svg, "imagens 3d")
            if not os.path.exists(self.output_path):
                os.makedirs(self.output_path)

            self._analisar_e_exibir_svg(file_path)

    def _avancar_para_processamento(self):
        if not self.svg_selecionado or not os.path.exists(self.svg_selecionado):
            messagebox.showwarning("Atenção", "Por favor, selecione um arquivo SVG antes de prosseguir.")
            return

        self.lbl_status_processamento.configure(text="🔄 Iniciando importação e montagem de malhas...")
        for widget in self.frame_historico.winfo_children():
            widget.destroy()
            
        self._show_screen("processing")
        self._iniciar_processamento_background()

    def _analisar_e_exibir_svg(self, caminho_svg):
        info = extrair_informacoes_svg(caminho_svg)
        self.txt_analise_svg.configure(state="normal")
        self.txt_analise_svg.delete("1.0", "end")

        if info:
            resumo = f"📁 ARQUIVO: {info['nome_arquivo']}\n"
            resumo += "─" * 40 + "\n"
            resumo += "📦 MATERIAIS & QUANTIDADES:\n"
            for (tipo, nome), qtd in info['materiais_qtd'].items():
                resumo += f" • [{tipo:<12}] {nome:<22} : {qtd}\n"
            resumo += "─" * 40 + "\n"
            resumo += f"📐 DIMENSÃO DO TROFÉU:\n"
            resumo += f" • Fundo    : {info['nome_fundo']}\n"
            resumo += f" • Largura  : {info['largura_mm']:.2f} mm ({info['largura_cm']:.2f} cm)\n"
            resumo += f" • Altura   : {info['altura_mm']:.2f} mm ({info['altura_cm']:.2f} cm)\n"
            self.txt_analise_svg.insert("1.0", resumo)
        else:
            self.txt_analise_svg.insert("1.0", "❌ Não foi possível extrair dados estruturais do SVG.")

        self.txt_analise_svg.configure(state="disabled")

    def _build_catalogo_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["catalogo"] = screen

        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=10, pady=10)

        header = tk.Frame(card, bg="#121824")
        header.pack(fill="x", padx=20, pady=15)
        
        tk.Label(header, text="📊 Mapeamento do Catálogo de Troféus", fg="#38BDF8", bg="#121824", font=("Helvetica", 14, "bold")).pack(side="left")
        tk.Button(header, text="🔄 Atualizar Catálogo", bg="#1E2638", fg="#FFFFFF", bd=0, padx=12, pady=6, font=("Helvetica", 9, "bold"), command=self._atualizar_relatorio_catalogo).pack(side="right")

        # Cor alterada para #34D399 (mesma cor da caixa de Análise do SVG)
        self.txt_catalogo = tk.Text(card, bg="#080C14", fg="#34D399", font=("Consolas", 9), bd=0, padx=15, pady=15)
        scrollbar = ttk.Scrollbar(card, command=self.txt_catalogo.yview)
        self.txt_catalogo.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.txt_catalogo.pack(side="left", fill="both", expand=True)

    def _atualizar_relatorio_catalogo(self):
        modalidades, status = mapear_catalogo(self.catalogo_dir)
        self.txt_catalogo.configure(state="normal")
        self.txt_catalogo.delete("1.0", "end")

        if not modalidades:
            self.txt_catalogo.insert("1.0", f"{status}\nCaminho configurado: {self.catalogo_dir}")
            self.txt_catalogo.configure(state="disabled")
            return

        relatorio = ""
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

            pastas_formatadas = textwrap.fill(f"Pastas Prontas: {pastas_str}", width=80, subsequent_indent="     ")

            relatorio += f"Modalidade: {mod}\n"
            relatorio += f"Status: {status_str}\n"
            relatorio += f"SVG Count: {svg_count}\n"
            relatorio += f"{pastas_formatadas}\n"
            relatorio += "────────────────────────────────────────\n"

        relatorio += "📈 Totais\n"
        relatorio += f"- Total pronto para catalogar: {total_geral_trofeus} troféus\n"
        for mod, qtd in totais_por_modalidade.items():
            relatorio += f"- {mod}: {qtd}\n"

        relatorio += "\n📝 Observações\n"
        relatorio += "- O critério de \"pronto\" é a presença de pelo menos um arquivo .svg em alguma subpasta\n"
        relatorio += "- Todos os relatórios padronizam em Português Brasileiro (PT-BR)\n"

        relatorio += "\n📁 Diretório do Catálogo\n"
        relatorio += f"{self.catalogo_dir}\n"

        self.txt_catalogo.insert("1.0", relatorio)
        self.txt_catalogo.configure(state="disabled")

    def _iniciar_processamento_background(self):
        threading.Thread(target=self._executar_blender_subprocess, daemon=True).start()

    def atualizar_amostras_camera_ui(self, atual, total, faltam, porcentagem, nome_cam):
        self.lbl_status_processamento.configure(text=f"📷 Renderizando: {nome_cam}")
        self.lbl_samples_info.configure(text=f"[{nome_cam}] Samples: {atual} / {total}  |  Faltam: {faltam}")
        self.atualizar_barra_progresso(porcentagem)

    def _executar_blender_subprocess(self):
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_engine = os.path.join(diretorio_atual, "blender_engine.py")

        caminho_blend_escolhido = ""
        if self.blend_dir and self.selected_blend and not self.selected_blend.startswith("Nenhum"):
            caminho_blend_escolhido = os.path.join(self.blend_dir, self.selected_blend)

        resina_escolhida = self.modelo_resina_selecionado.get()
        caminho_resina_completo = ""
        if resina_escolhida and not resina_escolhida.startswith("Nenhum"):
            caminho_resina_completo = os.path.join(self.resina_dir, resina_escolhida)

        comando = [self.blender_path]

        if self.render_auto_var.get():
            comando.append("--background")

        comando.extend([
            "--python", caminho_engine,
            "--",
            self.svg_selecionado,
            self.output_path,
            caminho_blend_escolhido,
            str(self.render_auto_var.get()),
            str(self.usar_textura_var.get()),
            str(self.cycles_samples),
            str(self.usar_verniz_var.get()),
            caminho_resina_completo
        ])

        try:
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            for linha in processo.stdout:
                linha_limpa = linha.strip()
                if "Carregando estúdio base" in linha_limpa:
                    self.after(0, lambda: self.lbl_status_processamento.configure(text="📂 Abrindo arquivo de estúdio base..."))
                elif "Analisando e importando" in linha_limpa:
                    self.after(0, lambda: self.adicionar_passo_concluido("✔ Estúdio carregado com sucesso!", "📐 Lendo dados do arquivo SVG..."))
                elif "Convertendo curvas" in linha_limpa:
                    self.after(0, lambda: self.adicionar_passo_concluido("✔ SVG importado com sucesso!", "⚙ Convertendo curvas e montando camadas..."))
                elif "Aplicando materiais" in linha_limpa:
                    self.after(0, lambda: self.adicionar_passo_concluido("✔ Malhas 3D montadas!", "🎨 Aplicando MDF, Acrílico e Texturas..."))
                elif "Renderizando câmera:" in linha_limpa:
                    cam_nome = linha_limpa.split("Renderizando câmera:")[-1].split("via")[0].strip()
                    self.after(0, lambda c=cam_nome: self.adicionar_passo_concluido("✔ Materiais aplicados com sucesso!", f"📷 Renderizando Câmera {c}..."))
                elif "[SAMPLE_PROGRESS]" in linha_limpa:
                    try:
                        parte_dados, parte_cam = linha_limpa.split("|CAM:")
                        amostras_str = parte_dados.split(" ")[1]
                        atual, total = map(int, amostras_str.split("/"))
                        porcentagem = (atual / total) * 100
                        faltam = total - atual
                        nome_cam_atual = parte_cam.strip()
                        self.after(0, lambda a=atual, t=total, f=faltam, p=porcentagem, c=nome_cam_atual: self.atualizar_amostras_camera_ui(a, t, f, p, c))
                    except Exception:
                        pass
                elif "Renders salvos em:" in linha_limpa or "Modo interativo ativo" in linha_limpa:
                    self.after(0, lambda: self.adicionar_passo_concluido("✔ Todas as imagens renderizadas!", "✅ Finalizando processo..."))

            processo.wait()
            self.after(0, lambda: self.tag_concluido())
        except Exception as e:
            messagebox.showerror("Erro Crítico", f"Não foi possível rodar o Blender:\n{e}")

    def atualizar_barra_progresso(self, porcentagem):
        largura_atual = self.canvas_barra.winfo_width()
        if largura_atual < 10:
            largura_atual = 440
        largura_preenchimento = (porcentagem / 100.0) * largura_atual
        self.canvas_barra.coords(self.retangulo_progresso, 0, 0, largura_preenchimento, 16)
        self.lbl_porcentagem.configure(text=f"{int(porcentagem)}%")

    def adicionar_passo_concluido(self, texto_concluido, novo_status):
        lbl_hist = tk.Label(self.frame_historico, text=texto_concluido, fg="#34D399", bg="#121824", font=("Helvetica", 9, "bold"), anchor="w")
        lbl_hist.pack(fill="x", pady=2)
        self.lbl_status_processamento.configure(text=novo_status)

    def tag_concluido(self):
        self.lbl_status_processamento.configure(text="✅ Processamento Concluído!")
        self.atualizar_barra_progresso(100)
        self.lbl_samples_info.configure(text="Renderização Finalizada (100% Concluído)")
        self._show_screen("download")

    def _build_processing_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["processing"] = screen

        self._create_stepper(screen, active_step=2)
        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(card, text="Processando Troféu no Blender...", fg="#FFFFFF", bg="#121824", font=("Helvetica", 14, "bold")).pack(pady=(20, 5))
        self.lbl_status_processamento = tk.Label(card, text="🔄 Iniciando importação e montagem de malhas...", fg="#38BDF8", bg="#121824", font=("Helvetica", 11, "bold"))
        self.lbl_status_processamento.pack(pady=5)

        frame_progresso_container = tk.Frame(card, bg="#121824")
        frame_progresso_container.pack(fill="x", padx=40, pady=10)

        self.lbl_samples_info = tk.Label(frame_progresso_container, text="Aguardando início do Cycles...", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9, "bold"))
        self.lbl_samples_info.pack(anchor="w", pady=(0, 4))

        f_bar_bg = tk.Frame(frame_progresso_container, bg="#0B0F17", bd=1, relief="solid")
        f_bar_bg.pack(fill="x", ipady=2)
        
        self.canvas_barra = tk.Canvas(f_bar_bg, bg="#080C14", height=16, highlightthickness=0)
        self.canvas_barra.pack(fill="x")
        self.retangulo_progresso = self.canvas_barra.create_rectangle(0, 0, 0, 16, fill="#38BDF8", width=0)

        self.lbl_porcentagem = tk.Label(frame_progresso_container, text="0%", fg="#38BDF8", bg="#121824", font=("Helvetica", 9, "bold"))
        self.lbl_porcentagem.pack(anchor="e", pady=(2, 0))

        self.frame_historico = tk.Frame(card, bg="#121824")
        self.frame_historico.pack(fill="x", padx=40, pady=5)

    def _build_download_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["download"] = screen

        self._create_stepper(screen, active_step=3)
        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(card, text="Processamento Concluído!", fg="#34D399", bg="#121824", font=("Helvetica", 14, "bold")).pack(pady=(60, 10))
        tk.Button(card, text="Abrir Pasta de Imagens / Arquivos", fg="#FFFFFF", bg="#34D399", bd=0, padx=20, pady=10, font=("Helvetica", 10, "bold"), command=lambda: os.startfile(self.output_path) if os.path.exists(self.output_path) else None).pack(pady=20)

    def _build_footer(self):
        footer = tk.Frame(self, bg="#080C14", height=35, padx=20)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        tk.Label(footer, text="© 2026 VectorConvert Pro. All rights reserved.", fg="#4A5568", bg="#080C14", font=("Helvetica", 8)).pack(side="left", padx=10, pady=8)


if __name__ == "__main__":
    app = VectorConvertProApp()
    app.mainloop()