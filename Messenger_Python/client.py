import socket
import threading

def receive_messages(sock):
    """Odbiera wiadomości z serwera i wyświetla je."""
    while True:
        try:
            message = sock.recv(1024).decode()
            if not message:
                print("Połączenie z serwerem zostało przerwane.")
                break
            print(message)
        except Exception as e:
            print(f"Błąd przy odbieraniu wiadomości: {e}")
            break

def main():
    host = "localhost"
    port = 22345

    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((host, port))
        print("Połączono z serwerem.")
    except Exception as e:
        print(f"Nie udało się połączyć z serwerem: {e}")
        return

    username = input("Podaj swoją nazwę użytkownika: ").strip()
    client_socket.sendall(username.encode())

    # Sprawdź odpowiedź serwera (czy nazwa użytkownika jest unikalna)
    response = client_socket.recv(1024).decode()
    if "Nazwa użytkownika jest zajęta" in response:
        print(response)
        client_socket.close()
        return

    print(response)

    # Wątek do odbierania wiadomości
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.daemon = True
    receive_thread.start()

    # Główna pętla wysyłania wiadomości
    try:
        while True:
            message = input()
            if message.strip().lower() == "/end":
                client_socket.sendall("/END".encode())
                break
            client_socket.sendall(message.encode())
    except KeyboardInterrupt:
        print("\nZamykanie klienta...")
        client_socket.sendall("/END".encode())
    finally:
        client_socket.close()
        print("Połączenie zakończone.")

if __name__ == "__main__":
    main()
