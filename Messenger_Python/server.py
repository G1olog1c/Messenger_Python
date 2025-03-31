import threading
import socket
import os

# Katalog do przechowywania historii czatu
HISTORY_DIR = "chat_history"
os.makedirs(HISTORY_DIR, exist_ok=True)

# Lista aktywnych użytkowników
users = {}
# Lista wątków klientów
client_threads = []
# Lista wszystkich użytkowników, którzy kiedykolwiek się połączyli
all_users_file = os.path.join(HISTORY_DIR, "all_users.txt")
lock = threading.Lock()  # Blokada dla synchronizacji

# Flaga do zakończenia pracy serwera
server_running = True

def start_server():
    global server_running
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("localhost", 22345))
    server_socket.listen()
    print("Serwer nasłuchuje...")

    try:
        while server_running:
            try:
                conn, addr = server_socket.accept()
                thread = threading.Thread(target=handle_client, args=(conn, addr))
                client_threads.append(thread)
                thread.start()
            except Exception as e:
                print(f"Błąd przy akceptowaniu połączenia: {e}")
    except KeyboardInterrupt:
        print("Zamykanie serwera...")
        shutdown_server(server_socket)
    except Exception as e:
        print(f"Nieoczekiwany błąd: {e}")
    finally:
        server_socket.close()

def handle_client(conn, addr):
    username = None
    try:
        while True:
            conn.sendall("".encode())
            username = conn.recv(1024).decode().strip()

            if not username:
                conn.sendall("Nazwa użytkownika nie może być pusta. Spróbuj ponownie.".encode())
                continue

            if " " in username:
                conn.sendall("Nazwa użytkownika nie może zawierać spacji. Użyj jednej nazwy bez spacji.".encode())
                continue

            with lock:
                if username in users:
                    conn.sendall("Nazwa użytkownika jest już zajęta. Użyj innej lub wpisz /END, aby zakończyć połączenie.".encode())
                else:
                    users[username] = conn
                    save_all_user(username)
                    break

        print(f"Użytkownik {username} połączony z {addr}.")
        conn.sendall(f"Witaj, {username}! Możesz teraz wysyłać wiadomości.".encode())
        broadcast(f"{username} dołączył do czatu.", "Serwer", exclude_user=username)

        # Główna pętla obsługi klienta
        while True:
            try:
                message = conn.recv(1024).decode()
                if not message:
                    break

                # Obsługa poleceń
                if message.startswith("/"):
                    handle_commands(message, conn, username)
                elif message.startswith("@"):
                    handle_private_message(message, conn, username)
                else:
                    broadcast(message, username)
            except Exception as e:
                print(f"Błąd podczas odbierania od {username}: {e}")
                break

        # Rozłączenie użytkownika
        logout_user(username)
    except Exception as e:
        print(f"Błąd z użytkownikiem {addr}: {e}")
        if username:
            logout_user(username)
    finally:
        conn.close()
        with lock:
            remove_client_thread()

def remove_client_thread():
    """Usuwa bieżący wątek klienta z listy wątków."""
    current_thread = threading.current_thread()
    if current_thread in client_threads:
        client_threads.remove(current_thread)

def shutdown_server(server_socket):
    """Zamyka wszystkie wątki i połączenia oraz zamyka serwer."""
    global server_running
    server_running = False

    # Zamknięcie wszystkich klientów
    with lock:
        for user, conn in users.items():
            conn.close()
        users.clear()

    # Zamknięcie wszystkich wątków klientów
    for thread in client_threads:
        if thread.is_alive():
            thread.join()  # Czekamy na zakończenie wątku

    server_socket.close()
    print("Serwer został zamknięty.")

def handle_commands(message, conn, username):
    try:
        command = message.strip().upper()
        if command == "/LIST":
            handle_list_users(conn)
        elif command == "/ALLUSERS":
            send_all_users(conn)
        elif command == "/HISTORY":
            send_history(username, conn)
        elif command == "/END":
            logout_user(username)
            conn.sendall("Zamykanie połączenia...".encode())
            conn.close()  # Zamknięcie połączenia
        elif command == "/HELP":
            send_help(conn)
        else:
            conn.sendall("Nieznane polecenie. Wpisz /HELP, aby zobaczyć dostępne polecenia.".encode())
    except Exception as e:
        print(f"Błąd w obsłudze poleceń dla {username}: {e}")

def send_help(conn):
    help_message = (
        "Dostępne polecenia:\n"
        "/LIST - Wyświetla listę aktywnych użytkowników.\n"
        "/ALLUSERS - Wyświetla listę wszystkich użytkowników, którzy kiedykolwiek się połączyli.\n"
        "/HISTORY - Wyświetla historię czatu i prywatnych wiadomości.\n"
        "/END - Zamyka połączenie.\n"
        "@Nick <wiadomość> - Wysyła prywatną wiadomość do jednego lub więcej użytkowników, np. @user1,user2 Cześć!"
    )
    conn.sendall(help_message.encode())

def handle_private_message(message, conn, sender):
    try:
        if " " not in message:
            conn.sendall("Nieprawidłowy format. Użyj: @(Nick1,Nick2,...) <wiadomość>".encode())
            return

        recipient_section, msg = message.split(" ", 1)
        if not recipient_section.startswith("@") or len(recipient_section) <= 1:
            conn.sendall("Nieprawidłowy format. Użyj: @Nick1,Nick2,... <wiadomość>".encode())
            return

        recipients = [r.strip() for r in recipient_section[1:].split(",")]
        for recipient in recipients:
            send_private_message(sender, recipient, msg)
    except Exception as e:
        print(f"Błąd w obsłudze prywatnej wiadomości od {sender}: {e}")
        conn.sendall("Wystąpił błąd podczas wysyłania prywatnej wiadomości.".encode())

def handle_list_users(conn):
    """Wysyła listę aktywnych użytkowników do klienta."""
    with lock:
        user_list = "\n".join(users.keys())
    conn.sendall(f"Aktywni użytkownicy:\n{user_list}".encode())

def send_all_users(conn):
    """Wysyła listę wszystkich użytkowników, którzy kiedykolwiek się połączyli."""
    if os.path.exists(all_users_file):
        with open(all_users_file, "r", encoding="utf-8") as file:
            all_users = file.read()
        conn.sendall(f"Wszyscy użytkownicy:\n{all_users}".encode())
    else:
        conn.sendall("Brak danych o użytkownikach.".encode())

def send_private_message(sender, recipient, message):
    """Wysyła prywatną wiadomość do wybranego użytkownika."""
    with lock:
        if recipient in users:
            try:
                users[recipient].sendall(f"[Prywatna od {sender}]: {message}".encode())
                save_message(sender, recipient, message, private=True)
            except Exception as e:
                print(f"Błąd przy wysyłaniu prywatnej wiadomości od {sender} do {recipient}: {e}")
        else:
            if sender in users:
                users[sender].sendall(f"Użytkownik {recipient} nie jest online.".encode())

def broadcast(message, sender, exclude_user=None):
    """Wysyła wiadomość do wszystkich użytkowników, z wyjątkiem nadawcy."""
    with lock:
        disconnected_users = []
        for user, conn in users.items():
            if user != exclude_user:
                try:
                    conn.sendall(f"[{sender}]: {message}".encode())
                except Exception as e:
                    print(f"Błąd przy wysyłaniu wiadomości do {user}: {e}")
                    disconnected_users.append(user)

        for user in disconnected_users:
            del users[user]
    save_message(sender, "ALL", message)

def save_message(sender, recipient, message, private=False):
    """Zapisuje wiadomość w historii czatu."""
    if private:
        # Tworzenie nazwy pliku w alfabetycznym porządku nazw użytkowników
        participants = sorted([sender, recipient])
        filename = f"{HISTORY_DIR}/{participants[0]}_to_{participants[1]}.txt"
    else:
        filename = f"{HISTORY_DIR}/chat_history.txt"

    with open(filename, "a", encoding="utf-8") as file:
        file.write(f"[{sender} -> {recipient}]: {message}\n")

def send_history(username, conn):
    """Wysyła historię czatu do klienta."""
    # Wysyłanie historii ogólnego czatu
    history_file = f"{HISTORY_DIR}/chat_history.txt"
    if os.path.exists(history_file):
        with open(history_file, "r", encoding="utf-8") as file:
            history = file.read()
        conn.sendall(f"Ogólna historia czatu:\n{history}".encode())
    else:
        conn.sendall("Brak historii ogólnego czatu.".encode())

    # Wysyłanie historii prywatnych wiadomości
    private_history_files = [
        f for f in os.listdir(HISTORY_DIR)
        if username in f and f != "chat_history.txt"
    ]

    if private_history_files:
        conn.sendall("\nTwoje prywatne wiadomości:\n".encode())
        for file in private_history_files:
            with open(f"{HISTORY_DIR}/{file}", "r", encoding="utf-8") as f:
                conn.sendall(f.read().encode())
    else:
        conn.sendall("\nBrak prywatnych wiadomości.".encode())

def save_all_user(username):
    """Zapisuje użytkownika do pliku wszystkich użytkowników, jeśli jeszcze go tam nie ma."""
    if os.path.exists(all_users_file):
        with open(all_users_file, "r", encoding="utf-8") as file:
            all_users = file.read().splitlines()
            if username in all_users:
                return  # Użytkownik już istnieje w pliku

    with open(all_users_file, "a", encoding="utf-8") as file:
        file.write(f"{username}\n")

def logout_user(username):
    """Wylogowuje użytkownika i usuwa go z listy aktywnych."""
    with lock:
        if username in users:
            del users[username]
    broadcast(f"{username} opuścił czat.", "Serwer")

start_server()
