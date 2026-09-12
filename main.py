# -*- coding: utf-8 -*-
"""
DACLA - a Jarvis-style personal AI agent for your phone.
Free and open source (MIT). Brain: Google Gemini API free tier.
Voice: Android SpeechRecognizer + TextToSpeech. Memory: local JSON.
"""
import json, os, threading

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle

API_URL = ("https://generativelanguage.googleapis.com/v1beta/models/"
           "gemini-2.5-flash:generateContent")

PERSONA = (
    "You are Dacla, a Jarvis-style personal AI butler: sharp, witty, loyal and "
    "efficient. Speak like a modern Jarvis - calm, confident, a touch of dry "
    "humor, never robotic. Replies are spoken aloud, so keep them SHORT: 1 to "
    "3 sentences unless the user asks for detail. Remember personal facts the "
    "user shares and use them naturally."
)

IS_ANDROID = ("ANDROID_ARGUMENT" in os.environ) or os.path.exists("/system/build.prop")

_tts = None
def speak(text):
    global _tts
    if not IS_ANDROID:
        return
    try:
        from jnius import autoclass
        if _tts is None:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
            _tts = TextToSpeech(PythonActivity.mActivity, None)
        _tts.speak(text, TextToSpeech.QUEUE_FLUSH, None)
    except Exception as e:
        print("TTS error:", e)

def request_mic_permission():
    if not IS_ANDROID:
        return
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.RECORD_AUDIO, Permission.INTERNET])
    except Exception as e:
        print("Permission request failed:", e)


class DaclaApp(App):

    def build(self):
        self.title = "Dacla"
        self.cfg = self._load("config.json", {"api_key": ""})
        self.memory = self._load("memory.json", {"history": []})
        request_mic_permission()
        self._bind_stt()

        root = BoxLayout(orientation="vertical", padding=10, spacing=10)
        with root.canvas.before:
            Color(0.02, 0.05, 0.09, 1)
            self._bg = Rectangle(size=root.size, pos=root.pos)
        root.bind(size=self._update_bg, pos=self._update_bg)

        header = BoxLayout(size_hint_y=None, height=42, spacing=8)
        title = Label(text="[b]D A C L A[/b]  -  at your service",
                      markup=True, color=(0.45, 0.85, 1.0, 1),
                      font_size="20sp")
        gear = Button(text="⚙", size_hint_x=None, width=42,
                      background_color=(0.1, 0.2, 0.3, 1))
        gear.bind(on_release=self._open_settings)
        header.add_widget(title)
        header.add_widget(gear)
        root.add_widget(header)

        self.chat = Label(size_hint_y=None, markup=True,
                          color=(0.85, 0.95, 1.0, 1),
                          valign="top", padding=(8, 8))
        self.chat.bind(texture_size=self._chat_size)
        self.chat.text_size = (Window.width - 40, None)
        scroll = ScrollView()
        scroll.add_widget(self.chat)
        root.add_widget(scroll)

        row = BoxLayout(size_hint_y=None, height=52, spacing=8)
        self.entry = TextInput(hint_text="Ask Dacla anything...",
                               multiline=False,
                               background_color=(0.07, 0.12, 0.18, 1),
                               foreground_color=(0.9, 0.95, 1, 1),
                               cursor_color=(0.45, 0.85, 1, 1))
        self.entry.bind(on_text_validate=self._typed)
        mic = Button(text="🎤", size_hint_x=None, width=56,
                     background_color=(0.0, 0.35, 0.55, 1),
                     font_size="22sp")
        mic.bind(on_release=self.listen)
        send = Button(text="➤", size_hint_x=None, width=52,
                      background_color=(0.0, 0.45, 0.7, 1),
                      font_size="20sp")
        send.bind(on_release=self._typed)
        row.add_widget(self.entry)
        row.add_widget(mic)
        row.add_widget(send)
        root.add_widget(row)

        Clock.schedule_once(
            lambda dt: self._line("DACLA",
                "Systems online. Tap the mic and speak, or type below."))
        return root

    def _update_bg(self, instance, value):
        self._bg.size = instance.size
        self._bg.pos = instance.pos

    def _chat_size(self, instance, value):
        instance.height = max(value[1], self.chat.parent.height
                              if self.chat.parent else value[1])

    def _safe(self, text):
        return text.replace("[", "(").replace("]", ")").replace("&", "&amp;")

    def _line(self, who, text):
        color = "#5ad1ff" if who == "DACLA" else "#9fff9f"
        self.chat.text += ("\n[b][color=%s]%s:[/color][/b] %s"
                           % (color, who, self._safe(text)))
        Clock.schedule_once(lambda dt: self._scroll_bottom())

    def _scroll_bottom(self):
        if self.chat.parent:
            self.chat.parent.scroll_y = 0

    def _data_path(self, name):
        return os.path.join(self.user_data_dir, name)

    def _load(self, name, default):
        try:
            with open(self._data_path(name), "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return dict(default)

    def _save(self, name, data):
        try:
            with open(self._data_path(name), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
        except Exception as e:
            print("Save failed:", e)

    def _bind_stt(self):
        if not IS_ANDROID:
            return
        try:
            from android import activity as android_activity
            android_activity.bind(on_activity_result=self._on_activity_result)
        except Exception as e:
            print("STT bind failed:", e)

    def listen(self, *_):
        if not IS_ANDROID:
            self._line("DACLA",
                "Voice input needs the Android app - but I can still chat by typing!")
            return
        try:
            from jnius import autoclass
            Intent = autoclass("android.content.Intent")
            RI = autoclass("android.speech.RecognizerIntent")
            intent = Intent(RI.ACTION_RECOGNIZE_SPEECH)
            intent.putExtra(RI.EXTRA_LANGUAGE_MODEL,
                            RI.LANGUAGE_MODEL_FREE_FORM)
            intent.putExtra(RI.EXTRA_MAX_RESULTS, 1)
            intent.putExtra(RI.EXTRA_PROMPT, "Dacla is listening...")
            PA = autoclass("org.kivy.android.PythonActivity")
            PA.mActivity.startActivityForResult(intent, 42)
        except Exception as e:
            self._line("DACLA", "Microphone error: %s" % e)

    def _on_activity_result(self, request_code, result_code, intent):
        if request_code != 42 or intent is None:
            return
        try:
            from jnius import autoclass
            RI = autoclass("android.speech.RecognizerIntent")
            results = intent.getStringArrayListExtra(RI.EXTRA_RESULTS)
            if results and result_code == -1:
                text = str(results.get(0))
                Clock.schedule_once(lambda dt: self._heard(text))
            else:
                Clock.schedule_once(lambda dt: self._line(
                    "DACLA", "My apologies, I didn't catch that."))
        except Exception as e:
            print("STT result error:", e)

    def _typed(self, *_):
        text = self.entry.text.strip()
        if text:
            self.entry.text = ""
            self._heard(text)

    def _heard(self, text):
        self._line("YOU", text)
        threading.Thread(target=self._think, args=(text,),
                         daemon=True).start()

    def _think(self, text):
        if not self.cfg.get("api_key"):
            Clock.schedule_once(lambda dt: self._line(
                "DACLA",
                "I need a brain first. Tap ⚙ and paste your free Gemini API "
                "key (aistudio.google.com/apikey)."))
            return
        contents = []
        for h in self.memory["history"][-20:]:
            contents.append({
                "role": "user" if h["role"] == "user" else "model",
                "parts": [{"text": h["text"]}],
            })
        contents.append({"role": "user", "parts": [{"text": text}]})
        payload = {
            "system_instruction": {"parts": [{"text": PERSONA}]},
            "contents": contents,
        }
        try:
            import requests
            r = requests.post(API_URL, params={"key": self.cfg["api_key"]},
                              json=payload, timeout=60)
            data = r.json()
            reply = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            reply = "My neural pathways glitched for a moment: %s" % e
        self.memory["history"].append({"role": "user", "text": text})
        self.memory["history"].append({"role": "model", "text": reply})
        self.memory["history"] = self.memory["history"][-40:]
        self._save("memory.json", self.memory)
        Clock.schedule_once(lambda dt: self._reply(reply))

    def _reply(self, text):
        self._line("DACLA", text)
        speak(text)

    def _open_settings(self, *_):
        box = BoxLayout(orientation="vertical", padding=10, spacing=10)
        box.add_widget(Label(text="Paste your free Gemini API key below:",
                             size_hint_y=None, height=36))
        key_in = TextInput(text=self.cfg.get("api_key", ""),
                           multiline=False, hint_text="AIza...")
        box.add_widget(key_in)
        btns = BoxLayout(size_hint_y=None, height=48, spacing=10)
        save = Button(text="Save")
        wipe = Button(text="Erase memory")
        close = Button(text="Close")
        btns.add_widget(save)
        btns.add_widget(wipe)
        btns.add_widget(close)
        box.add_widget(btns)
        pop = Popup(title="Dacla Settings", content=box,
                    size_hint=(0.9, 0.5), auto_dismiss=True)

        def do_save(*_):
            self.cfg["api_key"] = key_in.text.strip()
            self._save("config.json", self.cfg)
            self._line("DACLA", "Brain connected. At your service.")
            pop.dismiss()
        save.bind(on_release=do_save)
        wipe.bind(on_release=lambda *_: (self.memory.update({"history": []}),
                                         self._save("memory.json", self.memory),
                                         self._line("DACLA", "Memory erased."),
                                         pop.dismiss()))
        close.bind(on_release=lambda *_: pop.dismiss())
        pop.open()


if __name__ == "__main__":
    DaclaApp().run()
