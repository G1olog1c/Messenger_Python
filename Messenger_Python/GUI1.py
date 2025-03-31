import tkinter as tk
from tkinter import scrolledtext, messagebox
import socket
import threading

def receive_messages(sock, text_area):
    """Odbiera wiadomości z serwera i wyświetla je w oknie tekstowym."""
    while True:
        try:
            message = sock.recv(1024).decode()
            if not message:
                break
            text_area.config(state=tk.NORMAL)
            if ":" in message:
                username, msg = message.split(":", 1)
                username = username.strip()
                if username.lower() == logged_in_username.lower():
                    text_area.insert(tk.END, f"{username}\n", ("current_user",))
                elif username.lower() == "serwer":
                    text_area.insert(tk.END, f"{username}\n", ("server",))
                else:
                    text_area.insert(tk.END, f"{username}\n", ("other_user",))
                text_area.insert(tk.END, f"{msg.strip()}\n", ("message",))
            else:
                text_area.insert(tk.END, message + "\n")
            text_area.yview(tk.END)
            text_area.config(state=tk.DISABLED)
        except Exception as e:
            print(f"Błąd przy odbieraniu wiadomości: {e}")
            break

def connect_to_server():
    """\u0141\u0105czy się z serwerem i inicjuje komunikację."""
    global client_socket, logged_in_username

    host = "localhost"
    port = 22345

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))

        username = username_entry.get().strip()
        if not username:
            messagebox.showerror("Błąd", "Nazwa użytkownika nie może być pusta.")
            return

        client_socket.sendall(username.encode())
        response = client_socket.recv(1024).decode()

        if "Nazwa użytkownika jest zajęta" in response:
            messagebox.showerror("Błąd", response)
            client_socket.close()
            return

        logged_in_username = username
        username_label.config(text=f"{username}")
        username_entry.pack_forget()
        login_button.pack_forget()
        message_entry.pack(side=tk.LEFT, padx=5, pady=5)
        send_button.pack(side=tk.LEFT, padx=5, pady=5)
        chat_area.config(state=tk.NORMAL)
        chat_area.insert(tk.END, response + "\n")
        chat_area.config(state=tk.DISABLED)

        # Odblokuj menu Opcje po zalogowaniu
        menu.entryconfig("Lista użytkowników", state="normal")
        menu.entryconfig("Lista wszystkich użytkowników", state="normal")
        menu.entryconfig("Historia czatu", state="normal")
        menu.entryconfig("Wyloguj", state="normal")

        # Uruchom wątek odbierania wiadomości
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket, chat_area))
        receive_thread.daemon = True
        receive_thread.start()

    except Exception as e:
        messagebox.showerror("Błąd", f"Nie udało się połączyć z serwerem: {e}")

def send_message(event=None):
    """Wysyła wiadomość wpisaną przez użytkownika."""
    message = message_entry.get().strip()
    if message:
        try:
            client_socket.sendall(message.encode())
            if message.lower() == "/end":
                client_socket.close()
                root.destroy()
            message_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Błąd", f"Nie udało się wysłać wiadomości: {e}")

def show_users():
    """Pokazuje listę użytkowników online."""
    client_socket.sendall("/list".encode())

def show_allusers():
    """Pokazuje listę WSZYSTKICH użytkowników."""
    client_socket.sendall("/allusers".encode())

def view_history():
    """Pobiera historię wiadomości."""
    client_socket.sendall("/history".encode())

def logout():
    """Wylogowuje użytkownika."""
    client_socket.sendall("/end".encode())
    root.destroy()

# Tworzenie głównego okna aplikacji
root = tk.Tk()
root.title("Komunikator")

# Górny pasek z nazwą użytkownika
username_label = tk.Label(root, text="Podaj swoją nazwę użytkownika:", font=("Arial", 12))
username_label.pack(pady=5)

# Pole na nazwę użytkownika
username_entry = tk.Entry(root, width=30)
username_entry.pack(pady=5)

# Przycisk logowania
login_button = tk.Button(root, text="Zaloguj", command=connect_to_server)
login_button.pack(pady=10)

# Okno czatu
chat_area = scrolledtext.ScrolledText(root, width=50, height=20, state=tk.DISABLED, wrap=tk.WORD)
chat_area.tag_config("current_user", foreground="blue", font=("Arial", 10, "italic"))
chat_area.tag_config("server", foreground="red", font=("Arial", 10, "italic"))
chat_area.tag_config("other_user", foreground="orange", font=("Arial", 10, "italic"))
chat_area.tag_config("message", font=("Arial", 12))
chat_area.pack(pady=10)

# Pole na wpisywanie wiadomości (ukryte przed zalogowaniem)
message_entry = tk.Entry(root, width=40)
message_entry.bind("<Return>", send_message)
message_entry.pack_forget()

# Przycisk wysyłania wiadomości (ukryty przed zalogowaniem)
send_button = tk.Button(root, text="Wyślij", command=send_message)
send_button.pack_forget()

# Dodatkowe funkcje w interfejsie
menu_bar = tk.Menu(root)
menu = tk.Menu(menu_bar, tearoff=0)
menu.add_command(label="Lista użytkowników", command=show_users, state="disabled")
menu.add_command(label="Lista wszystkich użytkowników", command=show_allusers, state="disabled")
menu.add_command(label="Historia czatu", command=view_history, state="disabled")
menu.add_separator()
menu.add_command(label="Wyloguj", command=logout, state="disabled")
menu_bar.add_cascade(label="Opcje", menu=menu)
root.config(menu=menu_bar)

root.mainloop()
