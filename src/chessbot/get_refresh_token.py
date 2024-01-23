import random
import socket
import asyncpraw
import asyncio


def main() -> None:
    asyncio.run(async_main())


async def async_main() -> None:
    scopes = ["read", "submit"]

    reddit = asyncpraw.Reddit(
        redirect_uri="http://localhost:8080",
        user_agent="obtain_refresh_token/v0 by u/bboe",
    )
    state = str(random.randint(0, 65000))
    url = reddit.auth.url(duration="permanent", scopes=scopes, state=state)
    print(f"Now open this url in your browser: {url}")

    client = receive_connection()
    data = client.recv(1024).decode("utf-8")
    param_tokens = data.split(" ", 2)[1].split("?", 1)[1].split("&")
    params = dict([token.split("=") for token in param_tokens])

    if state != params["state"]:
        send_message(
            client,
            f"State mismatch. Expected: {state} Received: {params['state']}",
        )
        exit(1)
    elif "error" in params:
        send_message(client, params["error"])
        exit(1)

    refresh_token = reddit.auth.authorize(params["code"])
    send_message(client, f"Refresh token: {refresh_token}")


def receive_connection() -> socket.socket:
    """Wait for and then return a connected socket..
    Opens a TCP connection on port 8080, and waits for a single client.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("localhost", 8080))
    server.listen(1)
    client = server.accept()[0]
    server.close()
    return client


def send_message(client: socket.socket, message: str) -> None:
    """Send message to client and close the connection."""
    print(message)
    client.send(f"HTTP/1.1 200 OK\r\n\r\n{message}".encode())
    client.close()


if __name__ == "__main__":
    main()
