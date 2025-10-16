"""
SecureSign
- Python + customtkinterFunciones:
    - Pestañas superiores (estilo Fluent/Windows 11)
    - Tema oscuro, fuente Segoe UI
    - Animación de fundido suave al cambiar de pestañas
    - Generación de claves (Ed25519), exportar/importar clave pública
    - Firmar archivos, exportar .sig
    - Verificar archivos con clave pública
- Dependencias:
    - customtkinter (>=5.0)
    - cryptography
- Instalación:
    - python -m pip install customtkinter cryptography
- Ejecutar:
    - python SecureSign_FluentUI_windows11_style.py
- Empaquetado opcional a .exe: usar pyinstaller.
"""

import os
import sys
import threading
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization

# -----------------------------
# Configuration / Constants
# -----------------------------
APP_TITLE = "SecureSign"
WINDOW_WIDTH = 820
WINDOW_HEIGHT = 520
FONT_FAMILY = "Segoe UI"  # Windows-like font; falls back if not available
ANIM_DURATION_MS = 200  # total fade duration when switching tabs

# -----------------------------
# Helper utilities
# -----------------------------

def threaded(fn):
    """Decorator to run a function in a daemon thread."""
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
        thr.start()
        return thr
    
    return wrapper


# -----------------------------
# Main application
# -----------------------------
class SecureSignApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Window
        self.title(APP_TITLE)
        try:
            # improve native look on Windows
            self.iconbitmap(default=self.resource_path("app_icon.ico"))
        except Exception:
            pass
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(760, 460)

        # Main grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top bar (title + tabs)
        self._create_top_bar()

        # Tab view (top tabs) - styled to look Fluent-like
        self.tabview = ctk.CTkTabview(self, width=20, height=20, corner_radius=12)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(12, 18))
        # place tabs on top
        self.tabview.add("🔑 Claves")
        self.tabview.add("✍️ Firma")
        self.tabview.add("✅ Verificar")

        # customize tabview layout padding to look 'paneled'
        self.tabview.tab("🔑 Claves").grid_columnconfigure(0, weight=1)
        self.tabview.tab("✍️ Firma").grid_columnconfigure(0, weight=1)
        self.tabview.tab("✅ Verificar").grid_columnconfigure(0, weight=1)

        # Frames (content per tab)
        self._setup_keys_tab(self.tabview.tab("🔑 Claves"))
        self._setup_sign_tab(self.tabview.tab("✍️ Firma"))
        self._setup_verify_tab(self.tabview.tab("✅ Verificar"))

        # status bar
        self.status = ctk.CTkLabel(self, text="Preparado", anchor="w", font=(FONT_FAMILY, 10))
        self.status.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))

        # animation binding when tab changed
        self.tabview.set("🔑 Claves")
        #self.tabview.bind("<<CTkTabviewTabChanged>>", self._on_tab_changed)

        # cryptographic keys (in-memory)
        self.private_key = None
        self.public_key = None

    def resource_path(self, relative_path: str) -> str:
        """Get absolute path to resource, useful for bundled apps."""
        try:
            base_path = sys._MEIPASS  # type: ignore
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def _create_top_bar(self):
        top = ctk.CTkFrame(self, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        left = ctk.CTkFrame(top, corner_radius=0)
        left.grid(row=0, column=0, sticky="w", padx=12, pady=8)

        title = ctk.CTkLabel(left, text=APP_TITLE, font=(FONT_FAMILY, 16, "bold"))
        title.pack(side="left")

        # subtle subtitle
        subtitle = ctk.CTkLabel(left, text="  — Firmar y Verificar • Ed25519", font=(FONT_FAMILY, 10))
        subtitle.pack(side="left")

        # right area: help and about
        right = ctk.CTkFrame(top, corner_radius=0)
        right.grid(row=0, column=1, sticky="e", padx=12, pady=8)
        help_btn = ctk.CTkButton(right, text="Ayuda", width=68, height=28, fg_color="transparent", command=self._show_help)
        help_btn.pack(side="right", padx=(6, 0))
        about_btn = ctk.CTkButton(right, text="Acerca de", width=68, height=28, fg_color="transparent", command=self._show_about)
        about_btn.pack(side="right", padx=(0, 6))

    def _show_help(self):
        messagebox.showinfo("Ayuda — SecureSign", "Pestañas:\n- Claves: Generar/exportar/importar claves públicas\n- Firmar: Firmar archivos con tu clave privada\n- Verificar: Verificar un archivo con una clave pública\n\nSe utiliza Ed25519 para firmas modernas.")

    def _show_about(self):
        messagebox.showinfo("Acerca de — SecureSign", f"{APP_TITLE}\n\nConstruido por Juan Arnau con customtkinter.\nAlgoritmo: Ed25519")

    # -----------------------------
    # Keys tab
    # -----------------------------
    def _setup_keys_tab(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(1, weight=1)

        lbl = ctk.CTkLabel(frame, text="Gestión de claves", font=(FONT_FAMILY, 14, "bold"))
        lbl.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(8, 18))

        gen_btn = ctk.CTkButton(frame, text="Generar par de claves Ed25519", command=self.generate_keys, height=36)
        gen_btn.grid(row=1, column=0, sticky="w", padx=10, pady=6)

        exp_btn = ctk.CTkButton(frame, text="Exportar clave pública (.pem)", command=self.export_public_key, height=36)
        exp_btn.grid(row=1, column=1, sticky="e", padx=10, pady=6)

        imp_btn = ctk.CTkButton(frame, text="Importar clave pública (.pem)", command=self.import_public_key, height=36)
        imp_btn.grid(row=2, column=0, sticky="w", padx=10, pady=6)

        # display area (public key preview)
        self.pub_preview = ctk.CTkTextbox(frame, height=160, corner_radius=8)
        self.pub_preview.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=10, pady=(12, 8))
        self.pub_preview.configure(state="disabled")

    # -----------------------------
    # Sign tab
    # -----------------------------
    def _setup_sign_tab(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(frame, text="Firmar archivo", font=(FONT_FAMILY, 14, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 18))

        sign_btn = ctk.CTkButton(frame, text="Seleccionar archivo y firmar", command=self.sign_file, height=42)
        sign_btn.grid(row=1, column=0, sticky="w", padx=10, pady=6)

        note = ctk.CTkLabel(frame, text="Formato de firma: bytes Ed25519 sin procesar guardados como archivo .sig", font=(FONT_FAMILY, 10))
        note.grid(row=2, column=0, sticky="w", padx=10, pady=(6, 0))

    # -----------------------------
    # Verify tab
    # -----------------------------
    def _setup_verify_tab(self, parent):
        frame = ctk.CTkFrame(parent, corner_radius=12)
        frame.grid(row=0, column=0, sticky="nsew", padx=12, pady=12)
        frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(frame, text="Verificar firma", font=(FONT_FAMILY, 14, "bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 18))

        verify_btn = ctk.CTkButton(frame, text="Seleccionar Archivo original + Firma + Clave Pública", command=self.verify_signature, height=42)
        verify_btn.grid(row=1, column=0, sticky="w", padx=10, pady=6)

        self.verify_result = ctk.CTkLabel(frame, text="", font=(FONT_FAMILY, 12))
        self.verify_result.grid(row=2, column=0, sticky="w", padx=10, pady=(12,0))

    # -----------------------------
    # Animations: fade out/in whole window on tab change
    # -----------------------------
    def _on_tab_changed(self, event):
        # perform a quick fade-out then fade-in to simulate a smooth transition
        self._fade_window()

    def _fade_window(self):
        # perform fade out and in; keep UI responsive
        steps = 8
        delay = ANIM_DURATION_MS // (2 * steps)
        # fade out
        for i in range(steps, -1, -1):
            alpha = i / steps
            try:
                self.attributes('-alpha', alpha)
                self.update()
            except Exception:
                pass
            time.sleep(delay/1000.0)
        # fade in
        for i in range(0, steps+1):
            alpha = i / steps
            try:
                self.attributes('-alpha', alpha)
                self.update()
            except Exception:
                pass
            time.sleep(delay/1000.0)

    # -----------------------------
    # Crypto operations
    # -----------------------------
    def generate_keys(self):
        self.private_key = Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        pem = self.public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                           format=serialization.PublicFormat.SubjectPublicKeyInfo)
        self._set_pub_preview(pem)
        self._set_status("Par de claves generado (Ed25519)")
        self.msg_info("Claves", "Ed25519 par de claves generado en la memoria.")

    def export_public_key(self):
        if not self.public_key:
            self.msg_error("Error de exportación", "No hay clave pública en la memoria. Genérela o impórtela primero.")
            return
        pem = self.public_key.public_bytes(encoding=serialization.Encoding.PEM,
                                           format=serialization.PublicFormat.SubjectPublicKeyInfo)
        path = filedialog.asksaveasfilename(defaultextension=".pem", filetypes=[("PEM", "*.pem")])
        if path:
            with open(path, 'wb') as f:
                f.write(pem)
            self._set_status(f"Clave pública exportada: {os.path.basename(path)}")

    def import_public_key(self):
        path = filedialog.askopenfilename(filetypes=[("PEM", "*.pem")])
        if not path:
            return
        with open(path, 'rb') as f:
            data = f.read()
        try:
            self.public_key = serialization.load_pem_public_key(data)
            self._set_pub_preview(data)
            self._set_status(f"Clave pública importada: {os.path.basename(path)}")
            messagebox.showinfo("Importar", "Clave pública importada con éxito.")
        except Exception as e:
            messagebox.showerror("Error de importación", f"no se pudo importar la clave pública:\n{e}")

    def sign_file(self):
        if not self.private_key:
            messagebox.showerror("Error de firma", "No hay clave privada en la memoria. Genere las claves primero.")
            return
        file_path = filedialog.askopenfilename(title="Seleccionar archivo para firmar")
        if not file_path:
            return
        with open(file_path, 'rb') as f:
            data = f.read()
        try:
            signature = self.private_key.sign(data)
            sig_path = filedialog.asksaveasfilename(defaultextension='.sig', filetypes=[('Signature', '*.sig')])
            if sig_path:
                with open(sig_path, 'wb') as f:
                    f.write(signature)
                self._set_status(f"Firmado: {os.path.basename(file_path)} -> {os.path.basename(sig_path)}")
                messagebox.showinfo("Firmado", "Archivo firmado y firma guardada.")
        except Exception as e:
            messagebox.showerror("Error de firma", f"Error al firmar el archivo:\n{e}")

    def verify_signature(self):
        file_path = filedialog.askopenfilename(title="Seleccionar archivo original")
        if not file_path:
            return
        sig_path = filedialog.askopenfilename(title="Seleccionar archivo de firma (.sig)")
        if not sig_path:
            return
        pub_path = filedialog.askopenfilename(title="Seleccionar clave pública (.pem)")
        if not pub_path:
            return
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            with open(sig_path, 'rb') as f:
                signature = f.read()
            with open(pub_path, 'rb') as f:
                pem = f.read()
            pub = serialization.load_pem_public_key(pem)
            pub.verify(signature, data)
            self.verify_result.configure(text="La firma es VÁLIDA ✅", text_color="green")
            self._set_status("Firma válida")
            messagebox.showinfo("Verificado", "La firma es válida.")
        except Exception as e:
            self.verify_result.configure(text="La firma NO ES VÁLIDA ❌", text_color="red")
            self._set_status("Firma inválida")
            messagebox.showerror("Error de verificación", f"Firma inválida o clave incorrecta:\n{e}")
    # -----------------------------
    # UI helpers
    # -----------------------------
    def _set_pub_preview(self, pem_bytes: bytes):
        txt = pem_bytes.decode(errors='ignore')
        self.pub_preview.configure(state="normal")
        self.pub_preview.delete("0.0", "end")
        self.pub_preview.insert("0.0", txt)
        self.pub_preview.configure(state="disabled")

    def _set_status(self, text: str):
        self.status.configure(text=text)

    # -----------------------------
    # Messagebox helpers con icono
    # -----------------------------
    def msg_info(self, title, message):
        """Muestra un messagebox de información con el icono de la app."""
        tmp = ctk.CTkToplevel(self)  # ventana temporal
        tmp.withdraw()
        try:
            tmp.iconbitmap(self.resource_path("app_icon.ico"))
        except Exception:
            pass
        messagebox.showinfo(title, message, parent=tmp)
        tmp.destroy()

    def msg_error(self, title, message):
        """Muestra un messagebox de error con el icono de la app."""
        tmp = ctk.CTkToplevel(self)
        tmp.withdraw()
        try:
            tmp.iconbitmap(self.resource_path("app_icon.ico"))
        except Exception:
            pass
        messagebox.showerror(title, message, parent=tmp)
        tmp.destroy()

# -----------------------------
# Run
# -----------------------------
if __name__ == '__main__':
    app = SecureSignApp()
    app.mainloop()
