import customtkinter
import cv2
from PIL import Image, ImageTk
import socket
import struct
import pickle
import atexit
import time
import json
import random
import threading
import math
import sqlite3

merkez_x = 300  # Added default value
merkez_y = 300  # Added default value

conn = sqlite3.connect('user_data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users 
             (username TEXT, password TEXT, ip TEXT, port INTEGER)''')

server_ip = None
server_port = None
client_socket = None
host_name = socket.gethostname()
ip_address = socket.gethostbyname(host_name)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 0))
port = s.getsockname()[1]

customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("green")

class TelemetryApplication(customtkinter.CTkFrame):
    def __init__(self, root):
        super().__init__(root)
        self.telemetry_data_labels = {}
        self.create_telemetry_labels()
        self.grid()  # TelemetryApplication olarak kullanıldığında grid() metodu çağrılabilir hale gelmeli

    def create_telemetry_labels(self):
        telemetry_labels = [
            "Enlem", "Boylam", "Irtifa", "Dikilme", "Yonelme", "Yatis",
            "Hiz", "Otonom", "Kilitlenme", "Hedef_Enlem", "Hedef_Boylam",
            "Hedef_Genislik", "Hedef_Yukseklik", "Batarya_Durumu"
        ]
        num_columns = 4
        for index, label_text in enumerate(telemetry_labels):
            row = index // num_columns * 2
            label_column = index % num_columns * 2
            value_column = label_column + 1

            label = customtkinter.CTkLabel(self, text=f"{label_text}: ")
            label.grid(row=row, column=label_column, sticky=customtkinter.W, pady=(0, 6))

            value_label = customtkinter.CTkLabel(self, text="")
            value_label.grid(row=row, column=value_column, sticky=customtkinter.W, pady=(0, 6))

            self.telemetry_data_labels[label_text] = value_label

        saat_label = customtkinter.CTkLabel(self, text="Saat:")
        saat_label.grid(row=14, column=0, sticky=customtkinter.W, pady=(0, 5))

        saat_value_label = customtkinter.CTkLabel(self, text="")
        saat_value_label.grid(row=14, column=1, sticky=customtkinter.W, pady=(0, 5))
        self.telemetry_data_labels["Saat"] = saat_value_label

    def veri_cek_telemetry(self):
        current_time = time.strftime("%H:%M:%S")
        telemetry_sinyali = {
            "Enlem": random.uniform(-90, 90),
            "Boylam": random.uniform(-180, 180),
            "Irtifa": random.uniform(0, 500),
            "Dikilme": random.uniform(-90, 90),
            "Yonelme": random.uniform(0, 360),
            "Yatis": random.choice([0, 1]),
            "Hiz": random.uniform(0, 200),
            "Otonom": random.choice([0, 1]),
            "Kilitlenme": random.choice([0, 1]),
            "Hedef_Enlem": random.uniform(-90, 90),
            "Hedef_Boylam": random.uniform(-180, 180),
            "Hedef_Genislik": random.uniform(10, 100),
            "Hedef_Yukseklik": random.uniform(5, 50),
            "Batarya_Durumu": random.uniform(0, 100),
            "Saat": current_time,
        }
        telemetry_json = json.dumps(telemetry_sinyali)
        return telemetry_json

    def veri_alan_thread_calistir_telemetry(self):
        while self.root.winfo_exists():
            json_verisi = self.veri_cek_telemetry()
            if json_verisi:
                self.update_telemetry(json_verisi)  # Burada update_telemetry çağrısı ekledik
            time.sleep(1)

    def update_telemetry(self, json_verisi):
        telemetry_sinyali = json.loads(json_verisi)
        for label_text, value_label in self.telemetry_data_labels.items():
            if label_text in telemetry_sinyali:
                value = telemetry_sinyali[label_text]
                value_label.configure(text=f"{value}")

def connect_to_server():
    global server_ip, server_port, client_socket, error_label

    if not server_ip or not server_port:
        error_label.config(text="Sunucu IP ve Port gerekli!")
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    while True:
        try:
            client_socket.connect((server_ip, server_port))
            return client_socket
        except ConnectionRefusedError as e:
            print(f"Bağlantı hatası: {str(e)}")
            time.sleep(2)
def close_socket():
    global client_socket
    if client_socket:
        client_socket.close()

atexit.register(close_socket)

def update_camera():
    global client_socket, camera_canvas
    try:
        if client_socket is None:
            print("Client socket is None, trying to connect...")
            client_socket = connect_to_server()

        if client_socket is not None:
            print("Connected to server, processing data...")

            data = b""
            payload_size = struct.calcsize("Q")

            while len(data) < payload_size:
                packet = client_socket.recv(4 * 1024)
                if not packet:
                    break
                data += packet
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack("Q", packed_msg_size)[0]

            print(f"Expected message size: {msg_size}")

            while len(data) < msg_size:
                data += client_socket.recv(4 * 1024)
            frame_data = data[:msg_size]
            data = data[msg_size:]

            frame = pickle.loads(frame_data)

            print("Processed frame data")

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (800, 600))
            frame = cv2.flip(frame, 1)
            photo = ImageTk.PhotoImage(image=Image.fromarray(frame))

            def update_canvas():
                camera_canvas.create_image(0, 0, image=photo, anchor=customtkinter.NW)
                camera_canvas.photo = photo

            camera_canvas.after(0, update_canvas)
            camera_canvas.after(20, update_camera)

        else:
            print("Client socket is None, cannot update camera")

    except Exception as e:
        print(f"Hata oluştu: {str(e)}")

def save_user_info(username, password, ip, port):
    c.execute('DELETE FROM users')
    c.execute('INSERT INTO users VALUES (?, ?, ?, ?)', (username, password, ip, port))
    conn.commit()

def exit_dashboard():
    global client_socket
    if client_socket is not None:
        client_socket.close()
    save_user_info(entry1.get(), entry2.get(), entry3.get(), entry4.get())
    root.destroy()

def load_user_data():
    c.execute('SELECT * FROM users')
    user_info = c.fetchone()
    return user_info if user_info else (None, None, None, None)

def fill_login_fields():
    user_info = load_user_data()
    if user_info:
        entry1.insert(customtkinter.END, str(user_info[0]))
        entry2.insert(customtkinter.END, str(user_info[1]))
        entry3.insert(customtkinter.END, str(user_info[2]))
        entry4.insert(customtkinter.END, str(user_info[3]))

registered_users = {
    "selim": {"password": "1234"},
    "furkan": {"password": "1234"},
    "emir": {"password": "1234"},
    "akif": {"password": "1234"},
    "deniz": {"password": "1234"}
}

def login():
    global server_ip, server_port, client_socket, remember_var

    entered_username = entry1.get()
    entered_password = entry2.get()
    entered_ip = entry3.get()
    entered_port = entry4.get()

    user_info = registered_users.get(entered_username)
    if user_info and user_info["password"] == entered_password:
        server_ip = entered_ip
        server_port = int(entered_port)
        login_frame.destroy()
        create_dashboard()
        return

    print("Hatalı kullanıcı adı veya şifre!")
    save_credentials = remember_var.get()
    if save_credentials:
        save_user_info(entered_username, entered_password, entered_ip, entered_port)
    else:
        server_ip = entered_ip
        server_port = int(entered_port)

def create_radar():
    global create_radar_frame, dashboard, canvas

    create_radar_frame = customtkinter.CTkFrame(dashboard, width=800, height=600, corner_radius=10)
    create_radar_frame.pack(side=customtkinter.RIGHT, padx=20, pady=20)

    canvas = customtkinter.CTkCanvas(create_radar_frame, width=600, height=600, bg="black")
    canvas.pack(fill="both", expand=True)

    veri_alan_thread = threading.Thread(target=veri_alan_thread_calistir)
    veri_alan_thread.start()

    ciz_radar_halkalari()
    ciz_eksenleri()

def ciz_radar_halkalari():
    global canvas
    halka_renkleri = ["green", "light green", "green", "light green", "green", "light green"]
    for i in range(6):
        canvas.create_oval(
            merkez_x - (i + 1) * 50,
            merkez_y - (i + 1) * 50,
            merkez_x + (i + 1) * 50,
            merkez_y + (i + 1) * 50,
            outline=halka_renkleri[i]
        )

def ciz_eksenleri():
    global canvas
    canvas.create_line(0, merkez_y, 600, merkez_y, fill="#7CFC00")
    canvas.create_line(merkez_x, 0, merkez_x, 600, fill="#7CFC00")

def veri_alan_thread_calistir():
    while True:
        if not root.winfo_exists():
            break
        json_verisi = veri_cek_radar()
        if json_verisi:
            radar_guncelle(json_verisi)
        time.sleep(1)

def veri_cek_radar():
    radar_sinyali = {
        "mesafe": random.uniform(0, 100),
        "aci": random.uniform(0, 360),
        "hiz": random.uniform(0, 150),
    }
    radar_json = json.dumps(radar_sinyali)
    return radar_json

def radar_guncelle(json_verisi):
    global canvas
    radar_sinyali = json.loads(json_verisi)
    guncelle_radar_hedefi(radar_sinyali["mesafe"], radar_sinyali["aci"])
    x, y = get_x_y_for_distance_and_angle(radar_sinyali["mesafe"], radar_sinyali["aci"])

def get_x_y_for_distance_and_angle(mesafe, aci):
    global merkez_x, merkez_y
    x = merkez_x + mesafe * 3 * math.cos(math.radians(aci))
    y = merkez_y - mesafe * 3 * math.sin(math.radians(aci))
    return x, y

def guncelle_radar_hedefi(mesafe, aci):
    global canvas
    x, y = get_x_y_for_distance_and_angle(mesafe, aci)
    canvas.delete("hedef")
    canvas.create_oval(x - 10, y - 10, x + 10, y + 10, outline="red", fill="red", tags="hedef")

def create_dashboard():
    global client_socket, dashboard, camera_canvas, create_radar_frame

    dashboard = customtkinter.CTkToplevel()
    dashboard.attributes('-fullscreen', True)
    dashboard.title("Yer Kontrol İstasyonu")

    exit_button = customtkinter.CTkButton(dashboard, text="Çıkış", command=exit_dashboard)
    exit_button.pack(side=customtkinter.BOTTOM, anchor=customtkinter.SW, padx=20, pady=20)

    created_by_label = customtkinter.CTkLabel(dashboard, text="Created by Selimc1")
    created_by_label.place(x=1800, y=1050)

    telemetry_frame = customtkinter.CTkFrame(dashboard, width=800, height=200)
    telemetry_frame.place(x=20, y=20)

    telemetry_uygulamasi = TelemetryApplication(telemetry_frame)
    telemetry_uygulamasi.grid(row=0, column=0)

    def update_telemetry_values():
        json_verisi = telemetry_uygulamasi.veri_cek_telemetry()
        if json_verisi:
            telemetry_uygulamasi.update_telemetry(json_verisi)

    def start_telemetry_update():
        update_telemetry_values()
        telemetry_frame.after(500, start_telemetry_update)

    start_telemetry_update()

    create_radar()

    camera_frame = customtkinter.CTkFrame(dashboard, width=800, height=600, corner_radius=10)
    camera_frame.pack(side=customtkinter.LEFT, padx=20, pady=20)

    camera_canvas = customtkinter.CTkCanvas(camera_frame, width=800, height=600, bg="#2e2e2e")
    camera_canvas.pack(fill="both", expand=True)

    update_camera()

    root.withdraw()
    dashboard.protocol("WM_DELETE_WINDOW", exit_button)
    dashboard.mainloop()

root = customtkinter.CTk()
login_frame = customtkinter.CTkFrame(root)
window_width = 450
window_height = 450

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

x = (screen_width // 2) - (window_width // 2)
y = (screen_height // 2) - (window_height // 2)

root.geometry(f"{window_width}x{window_height}+{x}+{y}")

frame = customtkinter.CTkFrame(master=root)
frame.pack(pady=20, padx=60, fill="both", expand=True)

label = customtkinter.CTkLabel(master=frame, text="Login")
label.pack(padx=12, pady=10)

entry1 = customtkinter.CTkEntry(master=frame, placeholder_text="Username")
entry1.pack(padx=12, pady=10)

entry2 = customtkinter.CTkEntry(master=frame, placeholder_text="Password", show="*")
entry2.pack(padx=12, pady=10)

entry3 = customtkinter.CTkEntry(master=frame, placeholder_text="Ip Address")
entry3.pack(padx=12, pady=10)

entry4 = customtkinter.CTkEntry(master=frame, placeholder_text="Port")
entry4.pack(padx=12, pady=10)

button = customtkinter.CTkButton(master=frame, text="Login", command=login)
button.pack(padx=12, pady=10)

remember_var = customtkinter.BooleanVar()
checkbox = customtkinter.CTkCheckBox(master=frame, text="Remember Me", variable=remember_var)
checkbox.pack(padx=12, pady=10)

fill_login_fields()

root.mainloop()