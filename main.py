import json
import os
import threading
import time
import urllib.error
import urllib.request
import flet as ft

API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-flash-latest"]
history = []


def ask_gemini(user_text: str, key: str) -> str:
    active_key = (key or API_KEY).strip()
    if not active_key:
        return "Введите API-ключ в настройках сверху."
    history.append({"role": "user", "parts": [{"text": user_text}]})
    payload = json.dumps({"contents": history}).encode("utf-8")
    last_error = "Неизвестная ошибка"

    for model in MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={active_key}"
        )
        for attempt in range(3):
            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    reply = data["candidates"][0]["content"]["parts"][0]["text"]
                    history.append({"role": "model", "parts": [{"text": reply}]})
                    return reply
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="replace")
                last_error = f"Ошибка HTTP {e.code}: {body}"
                if e.code == 503 and attempt < 2:
                    time.sleep(3)
                    continue
                break
            except Exception as e:
                last_error = f"Ошибка запроса: {e}"
                break
    history.pop()
    return last_error


def main(page: ft.Page):
    page.title = "Мой ИИ-Агент"
    page.bgcolor = "#111827"
    page.padding = 12

    key_field = ft.TextField(
        label="GEMINI_API_KEY",
        value=API_KEY,
        password=True,
        can_reveal_password=True,
        bgcolor="#1f2937",
        color="#ffffff",
        text_size=13,
        height=48,
    )

    chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    chat_list.controls.append(
        ft.Container(
            content=ft.Text(
                "Привет! Вставь ключ выше (если нужно) и напиши сообщение.",
                color="#e5e7eb",
            ),
            bgcolor="#1f2937",
            padding=12,
            border_radius=12,
        )
    )

    msg_input = ft.TextField(
        hint_text="Напиши сообщение...",
        expand=True,
        bgcolor="#374151",
        color="#ffffff",
        border_radius=10,
    )

    def run_request(text: str, key: str, thinking_box: ft.Container):
        answer = ask_gemini(text, key)
        if thinking_box in chat_list.controls:
            chat_list.controls.remove(thinking_box)
        chat_list.controls.append(
            ft.Container(
                content=ft.Text(answer, color="#e5e7eb"),
                bgcolor="#1f2937",
                padding=12,
                border_radius=12,
            )
        )
        page.update()

    def send_message(e=None):
        text = (msg_input.value or "").strip()
        if not text:
            return
        msg_input.value = ""
        chat_list.controls.append(
            ft.Container(
                content=ft.Text(text, color="#ffffff"),
                bgcolor="#2563eb",
                padding=12,
                border_radius=12,
            )
        )
        thinking = ft.Container(
            content=ft.Text("Думаю...", color="#9ca3af"),
            bgcolor="#1f2937",
            padding=12,
            border_radius=12,
        )
        chat_list.controls.append(thinking)
        page.update()

        threading.Thread(
            target=run_request,
            args=(text, key_field.value or "", thinking),
            daemon=True,
        ).start()

    msg_input.on_submit = send_message

    send_btn = ft.IconButton(
        icon=getattr(ft.Icons, "SEND", getattr(ft.Icons, "send", None)),
        icon_color="#ffffff",
        bgcolor="#2563eb",
        on_click=send_message,
    )

    page.add(
        key_field,
        chat_list,
        ft.Row([msg_input, send_btn]),
    )


if __name__ == "__main__":
    ft.run(main)


