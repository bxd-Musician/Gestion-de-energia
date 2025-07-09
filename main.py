import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import sys
import platform
import os


class EnergyMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Monitor de Consumo Energético")
        self.root.geometry("1024x768")

        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1*(event.delta/120)), "units"))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        main_frame = ttk.Frame(self.scrollable_frame, padding="10")
        main_frame.pack(expand=True, fill="both")

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill="x", pady=5)

        self.fig, (self.ax_cpu, self.ax_ram) = plt.subplots(1, 2, figsize=(10, 3))
        self.canvas = FigureCanvasTkAgg(self.fig, master=top_frame)
        self.canvas.get_tk_widget().pack(side="left", fill="both", expand=True, padx=5)
        
        self.cpu_data = [0] * 50
        self.ram_data = [0] * 50
        
        self.setup_plots()

        system_info_frame = ttk.LabelFrame(top_frame, text="Estado del Sistema", padding="10")
        system_info_frame.pack(side="right", fill="y", padx=5)

        self.battery_label = ttk.Label(system_info_frame, text="Batería: N/A")
        self.battery_label.pack(anchor="w")
        self.temp_label = ttk.Label(system_info_frame, text="Temp. CPU: N/A")
        self.temp_label.pack(anchor="w")
        self.disk_label = ttk.Label(system_info_frame, text="Uso de Disco: N/A")
        self.disk_label.pack(anchor="w")
        self.net_label = ttk.Label(system_info_frame, text="Red (Subida/Bajada): N/A")
        self.net_label.pack(anchor="w")

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(expand=True, fill="both", pady=5)
        
        process_frame = ttk.LabelFrame(bottom_frame, text="Procesos", padding="10")
        process_frame.pack(expand=True, fill="both")

        self.tree = ttk.Treeview(process_frame, columns=("pid", "name", "cpu", "ram", "energy_score"), show="headings")
        self.tree.heading("pid", text="PID", command=lambda: self.sort_treeview("pid", False))
        self.tree.heading("name", text="Nombre", command=lambda: self.sort_treeview("name", False))
        self.tree.heading("cpu", text="CPU %", command=lambda: self.sort_treeview("cpu", True))
        self.tree.heading("ram", text="RAM %", command=lambda: self.sort_treeview("ram", True))
        self.tree.heading("energy_score", text="Puntaje Energía", command=lambda: self.sort_treeview("energy_score", True))

        self.tree.column("pid", width=60, anchor="center")
        self.tree.column("name", width=250)
        self.tree.column("cpu", width=80, anchor="center")
        self.tree.column("ram", width=80, anchor="center")
        self.tree.column("energy_score", width=120, anchor="center")

        scrollbar_tree = ttk.Scrollbar(process_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar_tree.set)
        
        self.tree.pack(side="left", expand=True, fill="both")
        scrollbar_tree.pack(side="right", fill="y")
        
        kill_button = ttk.Button(bottom_frame, text="Terminar Proceso Seleccionado", command=self.kill_selected_process)
        kill_button.pack(pady=5)

        profile_frame = ttk.LabelFrame(bottom_frame, text="Gestión de Energía", padding="10")
        profile_frame.pack(fill="x", pady=5)

        ttk.Label(profile_frame, text="Perfil de energía:").pack(side="left", padx=5)
        self.profile_var = tk.StringVar(value="Balanceado")
        profile_menu = ttk.OptionMenu(profile_frame, self.profile_var, "Balanceado", "Ahorro máximo", "Balanceado", "Alto rendimiento", command=self.apply_energy_profile)
        profile_menu.pack(side="left", padx=5)

        ttk.Button(profile_frame, text="Suspender Sistema", command=self.suspend_system).pack(side="right", padx=5)
        ttk.Button(profile_frame, text="Apagar Pantalla", command=self.turn_off_screen).pack(side="right", padx=5)

        self.running = True
        self.update_thread = threading.Thread(target=self.update_data, daemon=True)
        self.update_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def apply_energy_profile(self, selected=None):
        perfil = self.profile_var.get()
        if perfil == "Ahorro máximo":
            self.update_interval = 5
            self.terminate_heavy_processes()
        elif perfil == "Balanceado":
            self.update_interval = 2
        elif perfil == "Alto rendimiento":
            self.update_interval = 1

    def terminate_heavy_processes(self):
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                cpu = proc.info['cpu_percent']
                mem = proc.info['memory_percent']
                energy_score = (cpu * 0.8) + (mem * 0.2)
                if energy_score > 50:
                    proc.terminate()
            except:
                pass

    def check_battery_for_auto_mode(self):
        try:
            battery = psutil.sensors_battery()
            if battery and not battery.power_plugged and battery.percent < 20:
                self.profile_var.set("Ahorro máximo")
                self.apply_energy_profile()
        except:
            pass

    def suspend_system(self):
        if platform.system() == "Windows":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif platform.system() == "Linux":
            os.system("systemctl suspend")

    def turn_off_screen(self):
        if platform.system() == "Windows":
            os.system("nircmd.exe monitor off")
        elif platform.system() == "Linux":
            os.system("xset dpms force off")

    def setup_plots(self):
        self.ax_cpu.set_title("Uso de CPU (%)")
        self.ax_cpu.set_ylim(0, 100)
        self.cpu_line, = self.ax_cpu.plot(self.cpu_data, lw=2, color='cyan')

        self.ax_ram.set_title("Uso de RAM (%)")
        self.ax_ram.set_ylim(0, 100)
        self.ram_line, = self.ax_ram.plot(self.ram_data, lw=2, color='lime')

        self.fig.tight_layout()

    def update_plots(self):
        self.cpu_data.append(psutil.cpu_percent(interval=None))
        self.cpu_data = self.cpu_data[-50:]
        self.cpu_line.set_ydata(self.cpu_data)
        self.ax_cpu.set_ylim(0, max(100, max(self.cpu_data) + 10))

        self.ram_data.append(psutil.virtual_memory().percent)
        self.ram_data = self.ram_data[-50:]
        self.ram_line.set_ydata(self.ram_data)
        
        self.canvas.draw()

    def update_system_info(self):
        try:
            battery = psutil.sensors_battery()
            if battery:
                plugged = "Cargando" if battery.power_plugged else "Descargando"
                self.battery_label.config(text=f"Batería: {battery.percent:.0f}% ({plugged})")
            else:
                self.battery_label.config(text="Batería: No disponible")
        except Exception:
            self.battery_label.config(text="Batería: No disponible")

        try:
            if sys.platform == "win32":
                self.temp_label.config(text="Temp. CPU: N/A en Windows")
            else:
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    cpu_temp = temps['coretemp'][0].current
                    self.temp_label.config(text=f"Temp. CPU: {cpu_temp}°C")
                else:
                    self.temp_label.config(text="Temp. CPU: No disponible")
        except Exception:
             self.temp_label.config(text="Temp. CPU: No disponible")

        disk = psutil.disk_usage('/')
        self.disk_label.config(text=f"Uso de Disco: {disk.percent}%")

        net_io = psutil.net_io_counters()
        self.net_label.config(text=f"Red: {self.bytes_to_gb(net_io.bytes_sent)} GB ↑ / {self.bytes_to_gb(net_io.bytes_recv)} GB ↓")

    def bytes_to_gb(self, b):
        return round(b / (1024**3), 2)
        
    def update_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                p_info = proc.info
                energy_score = (p_info['cpu_percent'] * 0.8) + (p_info['memory_percent'] * 0.2)
                processes.append((
                    p_info['pid'],
                    p_info['name'],
                    f"{p_info['cpu_percent']:.2f}",
                    f"{p_info['memory_percent']:.2f}",
                    f"{energy_score:.2f}"
                ))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if self.running:
            self.root.after(0, self._update_treeview_data, processes)
        
    def _update_treeview_data(self, processes):
        selected_item = self.tree.selection()
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        for p in processes:
            self.tree.insert("", "end", values=p)
            
        if selected_item:
            try:
                self.tree.selection_set(selected_item)
            except tk.TclError:
                pass

    def sort_treeview(self, col, reverse):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            data.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            data.sort(key=lambda t: t[0], reverse=reverse)

        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)

        self.tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def kill_selected_process(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Sin Selección", "Por favor, selecciona un proceso de la lista para terminarlo.")
            return

        item = selected_items[0]
        pid = self.tree.item(item, "values")[0]
        name = self.tree.item(item, "values")[1]
    
        if messagebox.askyesno("Confirmar", f"¿Estás seguro de que quieres terminar el proceso {name} (PID: {pid})?"):
            try:
                p = psutil.Process(int(pid))
                p.terminate()
                messagebox.showinfo("Éxito", f"El proceso {name} (PID: {pid}) ha sido terminado.")
            except psutil.NoSuchProcess:
                messagebox.showerror("Error", "El proceso ya no existe.")
            except psutil.AccessDenied:
                messagebox.showerror("Error", "Acceso denegado. Es posible que necesites ejecutar la aplicación como administrador.")
    
    def update_data(self):
        while self.running:
            self.update_plots()
            self.update_system_info()
            self.update_processes()
            self.check_battery_for_auto_mode()
            time.sleep(getattr(self, "update_interval", 2))

    def on_closing(self):
        self.running = False
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = EnergyMonitorApp(root)
    root.mainloop()
