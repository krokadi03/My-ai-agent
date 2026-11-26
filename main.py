import json
import os
import threading
import time
import urllib.error
import urllib.request
import flet as ft

DEFAULT_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest",
]

MODES = {
    "Универсал": (
        "Ты умный, находчивый ИИ-ассистент. Отвечай чётко, по делу, "
        "структурированно и без воды. Если задача сложная — разбивай её на понятные шаги."
    ),
    "Видеомонтажёр": (
        "Ты опытный режиссёр монтажа для коротких и длинных видео. "
        "Помогай планировать монтаж: разбивай сценарий или идею на кадры и склейки с таймингами, "
        "указывай, какие кадры показать, где сделать резкую склейку или переход, какой текст вывести на экран, "
        "формируй субтитры в формате .srt и при запросе давай точные команды ffmpeg для обрезки, склейки и субтитров."
    ),
    "Сценарии и Shorts": (
        "Ты опытный сценарист и продюсер коротких видео (Shorts, Reels, TikTok). "
        "Придумывай сильные хуки с первых секунд, пиши динамичные сценарии, "
        "готовые тексты для озвучки и при запросе оформляй субтитры в формате .srt с таймингами."
    ),
    "Код и проекты": (
        "Ты опытный разработчик. Пиши чистый, рабочий код без лишних зависимостей, "
        "объясняй причины ошибок простым языком и предлагай надёжные решения."
    ),
    "Перевод и текст": (
        "Ты профессиональный редактор и переводчик. Переводи естественно и точно, "
        "улучшай стиль текста, исправляй ошибки и предлагай несколько удачных вариантов."
    ),
}

QUICK_PROMPTS = [
    (
        "План монтажа",
        "Составь поминутный/посекундный план монтажа для ролика (какие кадры, склейки и текст на экране):\n",
    ),
    (
        "Склейка и обрезка",
        "Напиши пошаговый план склейки и обрезки клипов (и команды ffmpeg, если нужно):\n",
    ),
    (
        "Субтитры .srt",
        "Разбей этот текст на короткие фразы и оформи как субтитры .srt с таймингами:\n",
    ),
    (
        "Идея для видео",
        "Придумай 5 цепляющих идей для короткого видео с сильным началом.",
    ),
]

history = []


def make_welcome_bubble(mode_name: str) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            f"Готов к работе! Текущий режим: «{mode_name}».\n"
            "Выбери режим «Видеомонтажёр» сверху или нажми быструю кнопку для монтажа и субтитров.",
            color="#e5e7eb",
            size=13,
        ),
        bgcolor="#1f2937",
        padding=12,
        border_radius=12,
    )


def ask_gemini(user_text: str, key: str, selected_model: str, mode_name: str) -> str:
    active_key = (key or DEFAULT_API_KEY).strip()
    if not active_key:
        return "Вставь GEMINI_API_KEY в поле сверху."

    system_prompt = MODES.get(mode_name, MODES["Универсал"])
    history.append({"role": "user", "parts": [{"text": user_text}]})

    payload_dict = {
        "contents": history,
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "temperature": 0.7,
        },
    }
    payload = json.dumps(payload_dict).encode("utf-8")
    last_error = "Неизвестная ошибка"

    ordered_models = [selected_model] + [m for m in MODELS if m != selected_model]

    for model in ordered_models:
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
                last_error = f"Ошибка HTTP {e.code} ({model}): {body}"
                if e.code == 503 and attempt < 2:
                    time.sleep(2)
                    continue
                break
            except Exception as e:
                last_error = f"Ошибка запроса ({model}): {e}"
                break

    history.pop()
    return last_error


def main(page: ft.Page):
    page.title = "Мой ИИ-Агент Pro"
    page.bgcolor = "#111827"
    page.padding = 10

    saved_key = ""
    try:
        saved_key = page.client_storage.get("gemini_api_key") or ""
    except Exception:
        saved_key = ""

    def on_key_change(e):
        try:
            page.client_storage.set("gemini_api_key", (key_field.value or "").strip())
        except Exception:
            pass

    key_field = ft.TextField(
        label="GEMINI_API_KEY (сохраняется сам)",
        value=saved_key or DEFAULT_API_KEY,
        password=True,
        can_reveal_password=True,
        bgcolor="#1f2937",
        color="#ffffff",
        text_size=12,
        height=44,
        on_change=on_key_change,
    )

    mode_dropdown = ft.Dropdown(
        label="Режим ИИ",
        value="Видеомонтажёр",
        options=[ft.dropdown.Option(name) for name in MODES.keys()],
        bgcolor="#1f2937",
        color="#ffffff",
        text_size=12,
        expand=True,
    )

    model_dropdown = ft.Dropdown(
        label="Модель",
        value=MODELS[0],
        options=[ft.dropdown.Option(m) for m in MODELS],
        bgcolor="#1f2937",
        color="#ffffff",
        text_size=12,
        expand=True,
    )

    chat_list = ft.ListView(expand=True, spacing=10, auto_scroll=True)
    chat_list.controls.append(make_welcome_bubble(mode_dropdown.value or "Видеомонтажёр"))

    def copy_text(text_to_copy: str):
        page.set_clipboard(text_to_copy)
        page.snack_bar = ft.SnackBar(ft.Text("Скопировано в буфер обмена!"))
        page.snack_bar.open = True
        page.update()

    def build_ai_bubble(answer_text: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(answer_text, color="#e5e7eb", selectable=True, size=14),
                    ft.Row(
                        [
                            ft.TextButton(
                                content="Копировать",
                                on_click=lambda e, t=answer_text: copy_text(t),
                            )
                        ],
                        alignment=ft.MainAxisAlignment.END,
                    ),
                ],
                spacing=4,
            ),
            bgcolor="#1f2937",
            padding=12,
            border_radius=12,
        )

    def clear_chat(e=None):
        history.clear()
        chat_list.controls.clear()
        chat_list.controls.append(make_welcome_bubble(mode_dropdown.value or "Универсал"))
        page.update()

    def on_mode_change(e):
        clear_chat()

    mode_dropdown.on_change = on_mode_change

    clear_btn = ft.TextButton(
        content="Очистить",
        on_click=clear_chat,
    )

    msg_input = ft.TextField(
        hint_text="Опиши ролик, кадры или задачу для монтажа...",
        expand=True,
        multiline=True,
        min_lines=1,
        max_lines=4,
        bgcolor="#374151",
        color="#ffffff",
        border_radius=10,
    )

    def fill_prompt(prompt_prefix: str):
        msg_input.value = prompt_prefix
        page.update()

    quick_row = ft.Row(
        controls=[
            ft.OutlinedButton(
                content=label,
                on_click=lambda e, p=prefix: fill_prompt(p),
            )
            for label, prefix in QUICK_PROMPTS
        ],
        scroll=ft.ScrollMode.AUTO,
        spacing=6,
    )

    def run_request(
        text: str,
        key: str,
        selected_model: str,
        mode_name: str,
        thinking_box: ft.Container,
    ):
        answer = ask_gemini(text, key, selected_model, mode_name)
        if thinking_box in chat_list.controls:
            chat_list.controls.remove(thinking_box)
        chat_list.controls.append(build_ai_bubble(answer))
        page.update()

    def send_message(e=None):
        text = (msg_input.value or "").strip()
        if not text:
            return
        msg_input.value = ""
        chat_list.controls.append(
            ft.Container(
                content=ft.Text(text, color="#ffffff", size=14),
                bgcolor="#2563eb",
                padding=12,
                border_radius=12,
            )
        )
        thinking = ft.Container(
            content=ft.Text("Думаю...", color="#9ca3af", size=13),
            bgcolor="#1f2937",
            padding=12,
            border_radius=12,
        )
        chat_list.controls.append(thinking)
        page.update()

        threading.Thread(
            target=run_request,
            args=(
                text,
                key_field.value or "",
                model_dropdown.value or MODELS[0],
                mode_dropdown.value or "Универсал",
                thinking,
            ),
            daemon=True,
        ).start()

    send_btn = ft.IconButton(
        icon=getattr(ft.Icons, "SEND", getattr(ft.Icons, "send", None)),
        icon_color="#ffffff",
        bgcolor="#2563eb",
        on_click=send_message,
    )

    page.add(
        key_field,
        ft.Row([mode_dropdown, model_dropdown, clear_btn], spacing=6),
        chat_list,
        quick_row,
        ft.Row([msg_input, send_btn], spacing=6),
    )


if __name__ == "__main__":
    ft.run(main)

            


