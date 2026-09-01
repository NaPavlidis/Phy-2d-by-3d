import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Configurações do Sistema")
        self.geometry("580x400")
        self.configure(bg="#121824")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent_app = parent
        self.blender_path_var = tk.StringVar(value=parent.blender_path)
        self.output_path_var = tk.StringVar(value=parent.output_path)
        self.blend_dir_var = tk.StringVar(value=parent.blend_dir)
        self.selected_blend_var = tk.StringVar(value=parent.selected_blend)

        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="⚙ Configurações e Estúdios Base", fg="#FFFFFF", bg="#121824", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=20, pady=(15, 10))

        # Blender
        f_b = tk.Frame(self, bg="#121824")
        f_b.pack(fill="x", padx=20, pady=6)
        tk.Label(f_b, text="Executável do Blender (blender.exe):", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w", pady=(0, 2))
        sub_b = tk.Frame(f_b, bg="#121824")
        sub_b.pack(fill="x")
        tk.Entry(sub_b, textvariable=self.blender_path_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid", insertbackground="#FFFFFF").pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        tk.Button(sub_b, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_blender).pack(side="right")

        # Output
        f_o = tk.Frame(self, bg="#121824")
        f_o.pack(fill="x", padx=20, pady=6)
        tk.Label(f_o, text="Pasta de Saída dos Renders:", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w", pady=(0, 2))
        sub_o = tk.Frame(f_o, bg="#121824")
        sub_o.pack(fill="x")
        tk.Entry(sub_o, textvariable=self.output_path_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid", insertbackground="#FFFFFF").pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        tk.Button(sub_o, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_output).pack(side="right")

        # Pasta Blend
        f_d = tk.Frame(self, bg="#121824")
        f_d.pack(fill="x", padx=20, pady=6)
        tk.Label(f_d, text="Pasta com os Arquivos .Blend (Estúdios Base):", fg="#A0AEC0", bg="#121824", font=("Helvetica", 9)).pack(anchor="w", pady=(0, 2))
        sub_d = tk.Frame(f_d, bg="#121824")
        sub_d.pack(fill="x")
        tk.Entry(sub_d, textvariable=self.blend_dir_var, bg="#080C14", fg="#FFFFFF", bd=1, relief="solid", insertbackground="#FFFFFF").pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        tk.Button(sub_d, text="Buscar...", bg="#1E2638", fg="#FFFFFF", bd=0, padx=10, command=self._select_blend_dir).pack(side="right")

        # Dropdown Blend
        f_sel = tk.Frame(self, bg="#121824")
        f_sel.pack(fill="x", padx=20, pady=6)
        tk.Label(f_sel, text="Selecione o Estúdio Base (.blend) Ativo:", fg="#38BDF8", bg="#121824", font=("Helvetica", 9, "bold")).pack(anchor="w", pady=(0, 2))
        
        self.blend_dropdown_menu = tk.OptionMenu(f_sel, self.selected_blend_var, "")
        self.blend_dropdown_menu.config(bg="#080C14", fg="#FFFFFF", activebackground="#1E2638", activeforeground="#FFFFFF", bd=1, relief="solid", highlightthickness=0, width=50)
        self.blend_dropdown_menu["menu"].config(bg="#121824", fg="#FFFFFF", activebackground="#38BDF8", activeforeground="#000000")
        self.blend_dropdown_menu.pack(fill="x")
        self._atualizar_lista_blends()

        tk.Button(self, text="Salvar Configurações", bg="#38BDF8", fg="#FFFFFF", bd=0, font=("Helvetica", 10, "bold"), pady=8, command=self._save_settings).pack(fill="x", padx=20, pady=(15, 0))

    def _select_blender(self):
        f = filedialog.askopenfilename(title="Selecione o executável do Blender", filetypes=[("Executável Blender", "blender.exe"), ("Todos", "*.*")])
        if f: self.blender_path_var.set(f)

    def _select_output(self):
        f = filedialog.askdirectory(title="Selecione a Pasta de Saída dos Renders")
        if f: self.output_path_var.set(f)

    def _select_blend_dir(self):
        f = filedialog.askdirectory(title="Selecione a Pasta contendo os arquivos .blend")
        if f:
            self.blend_dir_var.set(f)
            self._atualizar_lista_blends()

    def _atualizar_lista_blends(self):
        pasta = self.blend_dir_var.get()
        menu = self.blend_dropdown_menu["menu"]
        menu.delete(0, "end")
        
        arquivos_blend = []
        if pasta and os.path.exists(pasta):
            arquivos_blend = [arq for arq in os.listdir(pasta) if arq.lower().endswith(".blend")]

        if arquivos_blend:
            for arq in arquivos_blend:
                menu.add_command(label=arq, command=lambda value=arq: self.selected_blend_var.set(value))
            if self.selected_blend_var.get() not in arquivos_blend:
                self.selected_blend_var.set(arquivos_blend[0])
        else:
            self.selected_blend_var.set("Nenhum arquivo .blend encontrado nesta pasta")
            menu.add_command(label="Nenhum arquivo .blend encontrado nesta pasta", command=lambda: None)

    def _save_settings(self):
        self.parent_app.blender_path = self.blender_path_var.get()
        self.parent_app.output_path = self.output_path_var.get()
        self.parent_app.blend_dir = self.blend_dir_var.get()
        self.parent_app.selected_blend = self.selected_blend_var.get()
        messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!", parent=self)
        self.destroy()


class VectorConvertProApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VectorConvert Pro")
        self.geometry("1100x750")
        self.configure(bg="#0B0F17")

        self.blender_path = r"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"
        self.output_path = os.path.join(os.getcwd(), "imagens")
        self.blend_dir = os.getcwd()
        self.selected_blend = ""
        self.svg_selecionado = ""
        
        # Variáveis dos Checkboxes
        self.render_auto_var = tk.BooleanVar(value=True)
        self.usar_textura_var = tk.BooleanVar(value=True) # Novo: Ativar/Desativar Texturização

        self.sidebar_buttons = {}
        self.screens = {}

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_navbar()
        self._build_sidebar()
        
        self.main_container = tk.Frame(self, bg="#0B0F17")
        self.main_container.grid(row=1, column=1, sticky="nsew", padx=40, pady=20)
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self._build_upload_screen()
        self._build_processing_screen()
        self._build_download_screen()

        self._build_footer()
        self._show_screen("upload")

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

        menu_items = {"upload": " Upload", "processing": " Processing", "download": " Download"}
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
        self.screens[screen_key].tkraise()

    def _create_stepper(self, parent, active_step):
        stepper_frame = tk.Frame(parent, bg="#0B0F17")
        stepper_frame.pack(fill="x", pady=(10, 30))

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
            tk.Label(step_item, text=label, fg=text_color, bg="#0B0F17", font=("Helvetica", 8, "bold")).pack(pady=(5, 0))

    def _build_upload_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["upload"] = screen

        self._create_stepper(screen, active_step=1)
        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(card, text="Faça o upload do seu arquivo SVG", fg="#FFFFFF", bg="#121824", font=("Helvetica", 14, "bold")).pack(pady=(30, 10))
        
        self.lbl_arquivo_selecionado = tk.Label(card, text="Nenhum arquivo selecionado", fg="#A0AEC0", bg="#121824", font=("Helvetica", 10))
        self.lbl_arquivo_selecionado.pack(pady=5)

        btn_select = tk.Button(card, text="Selecionar Arquivo SVG", fg="#FFFFFF", bg="#38BDF8", bd=0, padx=20, pady=10, font=("Helvetica", 10, "bold"), command=self._selecionar_svg)
        btn_select.pack(pady=15)

        # --- CHECKBOX 1: RENDERIZAÇÃO AUTOMÁTICA ---
        chk_render = tk.Checkbutton(
            card, text="Renderizar automaticamente após importar e montar", variable=self.render_auto_var, 
            fg="#A0AEC0", bg="#121824", selectcolor="#080C14", activebackground="#121824", activeforeground="#FFFFFF", font=("Helvetica", 9)
        )
        chk_render.pack(pady=5)

        # --- CHECKBOX 2: APLICAR TEXTURIZAÇÃO ---
        chk_textura = tk.Checkbutton(
            card, text="Aplicar texturas (Ex: madeira.jpg no MDF)", variable=self.usar_textura_var, 
            fg="#A0AEC0", bg="#121824", selectcolor="#080C14", activebackground="#121824", activeforeground="#FFFFFF", font=("Helvetica", 9)
        )
        chk_textura.pack(pady=5)

    def _selecionar_svg(self):
        file_path = filedialog.askopenfilename(title="Selecionar SVG", filetypes=[("Arquivos SVG", "*.svg"), ("Todos", "*.*")])
        if file_path:
            self.svg_selecionado = file_path
            self.lbl_arquivo_selecionado.configure(text=os.path.basename(file_path), fg="#34D399")
            self._show_screen("processing")
            self._iniciar_processamento_background()

    def _iniciar_processamento_background(self):
        threading.Thread(target=self._executar_blender_subprocess, daemon=True).start()

    def _executar_blender_subprocess(self):
        diretorio_atual = os.path.dirname(os.path.abspath(__file__))
        caminho_engine = os.path.join(diretorio_atual, "blender_engine.py")

        caminho_blend_escolhido = ""
        if self.blend_dir and self.selected_blend and not self.selected_blend.startswith("Nenhum"):
            caminho_blend_escolhido = os.path.join(self.blend_dir, self.selected_blend)

        comando = [self.blender_path]

        if self.render_auto_var.get():
            comando.append("--background")

        # Repassa todos os parâmetros atualizados para o motor do Blender
        comando.extend([
            "--python", caminho_engine,
            "--",
            self.svg_selecionado,
            self.output_path,
            caminho_blend_escolhido,
            str(self.render_auto_var.get()),
            str(self.usar_textura_var.get())
        ])

        try:
            print(f">>> Executando Blender (Render: {self.render_auto_var.get()}, Textura: {self.usar_textura_var.get()})")
            processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='ignore')
            for linha in processo.stdout:
                print(linha, end="")
            processo.wait()

            self.after(0, lambda: self._show_screen("download"))
        except Exception as e:
            print(f"Erro ao executar o Blender via subprocess: {e}")
            messagebox.showerror("Erro Crítico", f"Não foi possível rodar o Blender:\n{e}")

    def _build_processing_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["processing"] = screen

        self._create_stepper(screen, active_step=2)
        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(card, text="Processando Troféu no Blender...", fg="#FFFFFF", bg="#121824", font=("Helvetica", 14, "bold")).pack(pady=(60, 5))
        tk.Label(card, text="🔄 Aplicando estúdio base, importando curvas e montando malhas...", fg="#A0AEC0", bg="#121824", font=("Helvetica", 10)).pack(pady=(0, 20))

    def _build_download_screen(self):
        screen = tk.Frame(self.main_container, bg="#0B0F17")
        screen.grid(row=0, column=0, sticky="nsew")
        self.screens["download"] = screen

        self._create_stepper(screen, active_step=3)
        card = tk.Frame(screen, bg="#121824", bd=1, relief="solid")
        card.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(card, text="Processamento Concluído!", fg="#34D399", bg="#121824", font=("Helvetica", 14, "bold")).pack(pady=(60, 10))
        
        tk.Button(
            card, text="Abrir Pasta de Imagens / Arquivos", fg="#FFFFFF", bg="#34D399", bd=0, padx=20, pady=10, font=("Helvetica", 10, "bold"),
            command=lambda: os.startfile(self.output_path) if os.path.exists(self.output_path) else None
        ).pack(pady=20)

    def _build_footer(self):
        footer = tk.Frame(self, bg="#080C14", height=35, padx=20)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        tk.Label(footer, text="© 2026 VectorConvert Pro. All rights reserved.", fg="#4A5568", bg="#080C14", font=("Helvetica", 8)).pack(side="left", padx=10, pady=8)


if __name__ == "__main__":
    app = VectorConvertProApp()
    app.mainloop()