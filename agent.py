#!/usr/bin/env python3
import os
import sys
import json
import time
import argparse
from datetime import datetime
import urllib.request
import urllib.parse

# Intentar cargar variable de entorno desde un archivo .env local si existe (para evitar dependencias externas)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")
    except Exception:
        pass

# Verificar e importar dependencias necesarias
try:
    from google import genai
    from google.genai import types
except ImportError:
    print("ERROR: La librería 'google-genai' no está instalada. Ejecuta: pip3 install google-genai")
    sys.exit(1)

try:
    from instagrapi import Client
    from instagrapi.types import StoryMention
except ImportError:
    # Si estamos en cron, alertar. Si no, podemos fallar solo cuando se llame a Instagram
    pass

# Códigos de colores ANSI para la consola
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_CYAN = "\033[36m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_RED = "\033[31m"
COLOR_MAGENTA = "\033[35m"

# Mapeo de códigos de clima de Open-Meteo
WEATHER_CODES = {
    0: ("Despejado", "☀️"), 1: ("Principalmente despejado", "🌤️"), 2: ("Parcialmente nublado", "⛅"), 3: ("Nublado", "☁️"),
    45: ("Niebla", "🌫️"), 48: ("Niebla con escarcha", "🌫️❄️"), 51: ("Llovizna ligera", "🌧️"), 53: ("Llovizna moderada", "🌧️"),
    55: ("Llovizna densa", "🌧️"), 56: ("Llovizna helada ligera", "🌧️❄️"), 57: ("Llovizna helada densa", "🌧️❄️"),
    61: ("Lluvia débil", "🌧️"), 63: ("Lluvia moderada", "🌧️"), 65: ("Lluvia fuerte", "🌧️☔"), 66: ("Lluvia helada débil", "🌧️❄️"),
    67: ("Lluvia helada fuerte", "🌧️❄️"), 71: ("Nevada leve", "❄️"), 73: ("Nevada moderada", "❄️"), 75: ("Nevada fuerte", "❄️🌨️"),
    77: ("Granizo", "🌨️"), 80: ("Lluvia de chubascos débil", "🌦️"), 81: ("Lluvia de chubascos moderada", "🌦️"),
    82: ("Lluvia de chubascos violenta", "🌦️⛈️"), 85: ("Chubascos de nieve leves", "🌨️"), 86: ("Chubascos de nieve fuertes", "🌨️"),
    95: ("Tormenta eléctrica", "⛈️"), 96: ("Tormenta con granizo leve", "⛈️🌨️"), 99: ("Tormenta con granizo fuerte", "⛈️🌨️"),
}

def generate_content_with_fallback(gemini_client, prompt):
    models = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-flash-latest"]
    last_err = None
    for model_name in models:
        try:
            print(f"[Gemini] Intentando generar contenido con el modelo {model_name}...", flush=True)
            response = gemini_client.models.generate_content(model=model_name, contents=prompt)
            print(f"[Gemini] Éxito con el modelo {model_name}.", flush=True)
            return response
        except Exception as e:
            print(f"[Gemini] Error con el modelo {model_name}: {e}. Intentando el siguiente fallback...", flush=True)
            last_err = e
    raise last_err or Exception("Todos los modelos de Gemini fallaron.")

# --- HERRAMIENTAS LOCALES ---

def get_current_weather(city_name: str) -> str:
    """
    Obtiene la información del clima actual (temperatura, humedad, viento y condiciones) para una ciudad específica.
    """
    try:
        encoded_city = urllib.parse.quote(city_name)
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=es"
        req = urllib.request.Request(geocode_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
        if not data.get("results"):
            return json.dumps({"error": f"No se pudo encontrar la ciudad '{city_name}'."})
        result = data["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        name = result["name"]
        
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m&timezone=auto"
        req_weather = urllib.request.Request(weather_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req_weather) as response_weather:
            weather_data = json.loads(response_weather.read().decode())
        current = weather_data.get("current", {})
        temp = current.get("temperature_2m")
        feels_like = current.get("apparent_temperature")
        humidity = current.get("relative_humidity_2m")
        wind = current.get("wind_speed_10m")
        code = current.get("weather_code")
        weather_desc, emoji = WEATHER_CODES.get(code, ("Desconocido", "❓"))
        
        return json.dumps({
            "ciudad_encontrada": name,
            "temperatura": f"{temp}°C",
            "sensacion_termica": f"{feels_like}°C",
            "humedad": f"{humidity}%",
            "condicion": weather_desc,
            "emoji": emoji
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})

# --- CONEXIÓN INSTAGRAM ---

def get_instagram_client(dry_run=False):
    if dry_run:
        print(f"{COLOR_YELLOW}[DRY RUN] Simulación de conexión a Instagram activa.{COLOR_RESET}")
        return None
        
    username = os.environ.get("INSTAGRAM_USERNAME")
    password = os.environ.get("INSTAGRAM_PASSWORD")
    if not username or not password:
        print(f"{COLOR_RED}ERROR: Faltan las variables INSTAGRAM_USERNAME o INSTAGRAM_PASSWORD en el archivo .env{COLOR_RESET}")
        sys.exit(1)
        
    cl = Client()
    session_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")
    print(f"[Instagram] Buscando archivo de sesión en: {session_path}", flush=True)
    if os.path.exists(session_path):
        size = os.path.getsize(session_path)
        print(f"[Instagram] Archivo session.json encontrado (Tamaño: {size} bytes). Cargando...", flush=True)
        try:
            cl.load_settings(session_path)
            print(f"[Instagram] Configuración cargada. Validando sesión para user_id: {cl.user_id}...", flush=True)
            # Validar usando la API privada (V1)
            info = cl.user_info_v1(cl.user_id)
            print(f"[Instagram] Sesión cargada desde cache con éxito para @{info.username} (sin necesidad de login).", flush=True)
            return cl
        except Exception as e:
            import traceback
            print(f"[Instagram] Sesión previa no válida o expirada. Detalles del error:", flush=True)
            traceback.print_exc()
            print("[Instagram] Intentando login convencional...", flush=True)
    else:
        print("[Instagram] Archivo session.json no encontrado. Se requiere login convencional.", flush=True)
            
    try:
        print("[Instagram] Iniciando login convencional...", flush=True)
        cl.login(username, password)
        cl.dump_settings(session_path)
        print("[Instagram] Inicio de sesión convencional exitoso. Sesión guardada.", flush=True)
        return cl
    except Exception as e:
        print(f"{COLOR_RED}[Instagram] ERROR crítico al iniciar sesión convencional: {e}{COLOR_RESET}", flush=True)
        sys.exit(1)
# --- ACCIONES ---

def share_reels_to_stories(dry_run=False):
    print(f"\n{COLOR_BOLD}{COLOR_GREEN}=== Tarea: Compartir Reels a Historias ==={COLOR_RESET}")
    
    # Cargar historial de compartidos
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared_reels.txt")
    shared_ids = set()
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            shared_ids = {line.strip() for line in f if line.strip()}

    cl = get_instagram_client(dry_run)
    
    if dry_run:
        print("[DRY RUN] Simulación: Obteniendo Reels de la cuenta...")
        print("[DRY RUN] Simulación: Se compartiría el Reel más antiguo no compartido.")
        return

    try:
        user_id = cl.user_id
        print(f"Obteniendo Reels de la cuenta (ID: {user_id})...")
        reels = cl.user_clips(user_id, amount=20)
        
        # Filtrar Reels no compartidos, del año actual y que no contengan palabras excluidas (eventos pasados)
        current_year = datetime.now().year
        exclude_keywords = ["boulder beats", "boulderbeats", "liga", "evento", "clinica"]
        pending_reels = []
        for reel in reels:
            reel_id = str(getattr(reel, "pk", None) or getattr(reel, "id", None))
            reel_year = reel.taken_at.year if getattr(reel, "taken_at", None) else None
            
            # Verificar si la publicación contiene palabras excluidas (eventos)
            caption = (reel.caption_text or "").lower()
            has_exclude_kw = any(kw in caption for kw in exclude_keywords)
            
            if reel_id not in shared_ids and reel_year == current_year and not has_exclude_kw:
                pending_reels.append((reel_id, reel))
                
        if not pending_reels:
            print(f"No hay Reels nuevos de este año ({current_year}) que califiquen para compartir.")
            return
            
        # Seleccionar el más antiguo de los pendientes (el último de la lista devuelta por Instagram)
        reel_id_to_share, reel_to_share = pending_reels[-1]
        print(f"Reel seleccionado para compartir: ID {reel_id_to_share} - Código: {reel_to_share.code}")
        
        # Compartir a Historia
        print("Compartiendo Reel a Historias...")
        cl.media_share_to_story(reel_id_to_share)
        
        # Registrar en el historial
        with open(history_file, "a") as f:
            f.write(f"{reel_id_to_share}\n")
            
        print(f"{COLOR_GREEN}¡Reel {reel_to_share.code} compartido con éxito a Historias!{COLOR_RESET}")
        
    except Exception as e:
        print(f"{COLOR_RED}Error al compartir Reel: {str(e)}{COLOR_RESET}")

def reply_dms(dry_run=False):
    print(f"\n{COLOR_BOLD}{COLOR_GREEN}=== Tarea: Responder DMs de Clientes ==={COLOR_RESET}")
    
    # Cargar base de conocimiento FAQ
    faq_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "faq.json")
    if not os.path.exists(faq_path):
        print(f"{COLOR_RED}ERROR: No se encontró el archivo base de conocimiento faq.json{COLOR_RESET}")
        return
        
    with open(faq_path, "r", encoding="utf-8") as f:
        faq_data = f.read()

    cl = get_instagram_client(dry_run)
    
    # Inicializar cliente Gemini
    if not os.environ.get("GEMINI_API_KEY"):
        print(f"{COLOR_RED}ERROR: Falta la variable de entorno GEMINI_API_KEY en tu archivo .env{COLOR_RESET}")
        return
    gemini_client = genai.Client()

    if dry_run:
        print("[DRY RUN] Simulación: Buscando DMs no leídos...")
        # Simular un DM ficticio para probar Gemini
        test_msg = "Hola! quería saber qué horarios tienen para ir a escalar y si tienen arriendo de zapatillas?"
        print(f"[DRY RUN] Pregunta simulada del cliente: '{test_msg}'")
        
        prompt = f"""
        Eres el asistente automatizado de IA para la cuenta de Instagram de @gravitymallsport (un gimnasio de escalada en Mall Sport, Chile).
        Tu tarea es responder al siguiente mensaje de un cliente de manera amigable, motivadora y útil, utilizando la información oficial en tu base de conocimientos (FAQ).

        MENSAJE DEL CLIENTE:
        "{test_msg}"

        BASE DE CONOCIMIENTOS OFICIAL (FAQ):
        {faq_data}

        REGLAS DE RESPUESTA:
        1. Responde en español chileno natural, buena onda y motivado (ej: "¡Hola! ¿Cómo estás?", "¡Buena onda!").
        2. Usa terminología de escalada sutilmente (🧗, apretar, muro, boulder).
        3. SI la información para responder la pregunta está en el FAQ, úsala exactamente (horarios, tarifas, arriendos, ubicaciones, etc.).
        4. SI la información no está en el FAQ, di de forma muy educada que no tienes el detalle exacto ahora mismo pero que transferirás el mensaje a un administrador humano para que le responda a la brevedad. NO inventes precios, horarios o servicios que no estén en el FAQ.
        5. Mantén la respuesta concisa y directa, ideal para leer en Instagram DMs.
        """
        response = generate_content_with_fallback(gemini_client, prompt)
        print(f"[DRY RUN] Respuesta generada por Gemini:\n{COLOR_CYAN}{response.text}{COLOR_RESET}")
        return

    try:
        unread_threads = cl.direct_threads(selected_filter="unread")
        if not unread_threads:
            print("No tienes DMs sin leer. ¡Gran trabajo!")
            return
            
        print(f"Se encontraron {len(unread_threads)} chats no leídos.")
        for thread in unread_threads:
            if not thread.messages:
                continue
            
            last_msg = thread.messages[0]
            # Si el último mensaje es nuestro, no respondemos para evitar bucles
            if last_msg.user_id == cl.user_id:
                print(f"Hilo {thread.id}: El último mensaje es nuestro. Omitiendo.")
                continue
                
            user_query = last_msg.text
            print(f"Procesando mensaje de Thread {thread.id}: '{user_query}'")
            
            # Generar respuesta con Gemini
            prompt = f"""
            Eres el asistente automatizado de IA para la cuenta de Instagram de @gravitymallsport (un gimnasio de escalada en Mall Sport, Chile).
            Tu tarea es responder al siguiente mensaje de un cliente de manera amigable, motivadora y útil, utilizando la información oficial en tu base de conocimientos (FAQ).

            MENSAJE DEL CLIENTE:
            "{user_query}"

            BASE DE CONOCIMIENTOS OFICIAL (FAQ):
            {faq_data}

            REGLAS DE RESPUESTA:
            1. Responde en español chileno natural, buena onda y motivado (ej: "¡Hola! ¿Cómo estás?", "¡Buena onda!").
            2. Usa terminología de escalada sutilmente (🧗, apretar, muro, boulder).
            3. SI la información para responder la pregunta está en el FAQ, úsala exactamente (horarios, tarifas, arriendos, ubicaciones, etc.).
            4. SI la información no está en el FAQ, di de forma muy educada que no tienes el detalle exacto ahora mismo pero que transferirás el mensaje a un administrador humano para que le responda a la brevedad. NO inventes precios, horarios o servicios que no estén en el FAQ.
            5. Mantén la respuesta concisa y directa, ideal para leer en Instagram DMs.
            """
            
            response = generate_content_with_fallback(gemini_client, prompt)
            reply_text = response.text
            
            # Enviar mensaje
            print(f"Enviando respuesta a Thread {thread.id}...")
            cl.direct_answer(thread.id, reply_text)
            
            # Marcar como visto
            cl.direct_send_seen(thread.id, last_msg.id)
            print(f"{COLOR_GREEN}Mensaje respondido y marcado como visto.{COLOR_RESET}")
            
    except Exception as e:
        print(f"{COLOR_RED}Error al responder DMs: {str(e)}{COLOR_RESET}")

def generate_weekly_report(dry_run=False):
    print(f"\n{COLOR_BOLD}{COLOR_GREEN}=== Tarea: Reporte Semanal de Métricas ==={COLOR_RESET}")
    
    cl = get_instagram_client(dry_run)
    
    # Inicializar cliente Gemini
    if not os.environ.get("GEMINI_API_KEY"):
        print(f"{COLOR_RED}ERROR: Falta la variable de entorno GEMINI_API_KEY en tu archivo .env{COLOR_RESET}")
        return
    gemini_client = genai.Client()

    if dry_run:
        print("[DRY RUN] Simulación: Generando reporte ficticio...")
        followers, following, media_count = 12500, 430, 240
        posts_data = [
            {"code": "C123", "type": "Video/Reel", "likes": 500, "comments": 24, "plays": 4500, "taken_at": "2026-07-15", "caption": "Entrenamiento de fuerza en campus board 🧗💪 #gravity"},
            {"code": "C456", "type": "Photo", "likes": 250, "comments": 10, "plays": 0, "taken_at": "2026-07-13", "caption": "Muro renovado de boulder. ¡Vengan a probar las nuevas rutas! 🧗‍♀️"},
        ]
    else:
        try:
            user_id = cl.user_id
            print("Obteniendo información del perfil...")
            info = cl.user_info_v1(user_id)
            followers = info.follower_count
            following = info.following_count
            media_count = info.media_count
            
            print("Obteniendo las últimas 5 publicaciones...")
            medias = cl.user_medias(user_id, amount=5)
            posts_data = []
            for media in medias:
                media_type_str = "Foto"
                if media.media_type == 2:
                    media_type_str = "Video/Reel" if media.product_type == "clips" else "Video"
                elif media.media_type == 8:
                    media_type_str = "Carrusel"
                    
                posts_data.append({
                    "code": media.code,
                    "type": media_type_str,
                    "likes": media.like_count,
                    "comments": media.comment_count,
                    "plays": getattr(media, "play_count", 0) or getattr(media, "view_count", 0),
                    "taken_at": str(media.taken_at.date() if media.taken_at else ""),
                    "caption": media.caption_text or ""
                })
        except Exception as e:
            print(f"{COLOR_RED}Error al obtener métricas de Instagram: {str(e)}{COLOR_RESET}")
            return

    # Redactar reporte con Gemini
    posts_json = json.dumps(posts_data, indent=2, ensure_ascii=False)
    prompt = f"""
    Eres un analista de marketing experto y Community Manager de la cuenta @gravitymallsport (gimnasio de escalada en Chile).
    Analiza las siguientes estadísticas de Instagram y redacta un reporte de rendimiento completo, estructurado y profesional en formato Markdown.

    DATOS GENERALES DE LA CUENTA:
    - Seguidores totales: {followers}
    - Siguiendo: {following}
    - Total de publicaciones en la cuenta: {media_count}

    ÚLTIMAS PUBLICACIONES ANALIZADAS:
    {posts_json}

    INSTRUCCIONES DEL REPORTE:
    1. Dale un título atractivo y dinámico.
    2. Agrega un "Resumen Ejecutivo" con lo más destacado de la actividad.
    3. Detalla el rendimiento de las publicaciones (cuál funcionó mejor, qué tipos de contenido generan más engagement: Reels vs Fotos/Carruseles).
    4. Proporciona recomendaciones prácticas y accionables específicas para @gravitymallsport en la próxima semana (ej. ideas de videos, llamados a la acción recomendados, temas de escalada a explotar).
    5. Mantén un tono motivador, muy profesional y cercano a la cultura escaladora.
    """
    
    print("Gemini analizando estadísticas y redactando informe...")
    response = generate_content_with_fallback(gemini_client, prompt)
    report_md = response.text
    
    # Guardar reporte localmente
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reportes")
    os.makedirs(reports_dir, exist_ok=True)
    date_str = datetime.now().strftime("%Y_%m_%d")
    report_path = os.path.join(reports_dir, f"reporte_semanal_{date_str}.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)
        
    print(f"\n{COLOR_GREEN}¡Reporte de métricas generado y guardado en:{COLOR_RESET}")
    print(f"👉 [reporte_semanal_{date_str}.md](file://{report_path})\n")
    print(f"{COLOR_BOLD}=== VISTA PREVIA DEL INFORME ==={COLOR_RESET}\n")
    print(report_md)

# --- TAREA: REPOSTEAR MENCIONES ---

def repost_mentions(dry_run=False):
    print(f"\n{COLOR_BOLD}{COLOR_GREEN}=== Tarea: Repostear Menciones en Historias ==={COLOR_RESET}")
    
    # Cargar historial de menciones ya compartidas
    history_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reposted_mentions.txt")
    reposted_ids = set()
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            reposted_ids = {line.strip() for line in f if line.strip()}

    cl = get_instagram_client(dry_run)
    
    if dry_run:
        print("[DRY RUN] Simulación: Buscando DMs con menciones en historias...")
        return

    try:
        # Obtener los hilos de mensajes
        print("Obteniendo DMs recientes...")
        threads = cl.direct_threads(amount=15)
        
        reposted_any = False
        
        for thread in threads:
            # Revisar los últimos mensajes de cada chat
            for message in thread.messages[:5]:
                # Verificar si es un mensaje de compartir historia (mención)
                if message.item_type == "story_share" and message.user_id != cl.user_id:
                    story_share = getattr(message, "story_share", None)
                    if not story_share:
                        continue
                        
                    # Extraer el ID de la historia original
                    media = getattr(story_share, "media", None)
                    if not media:
                        continue
                        
                    media_id = str(getattr(media, "pk", None) or getattr(media, "id", None))
                    
                    # Evitar duplicados
                    if media_id in reposted_ids:
                        continue
                        
                    print(f"Nueva mención detectada en historia de ID {media_id} (Usuario ID: {message.user_id})")
                    
                    try:
                        # 1. Obtener información del usuario que nos etiquetó
                        user_info = cl.user_info_v1(message.user_id)
                        print(f"Descargando historia de @{user_info.username}...")
                        
                        # 2. Descargar la historia original
                        path = cl.story_download(media_id)
                        path_str = str(path)
                        
                        # 3. Crear el sticker de mención para dar créditos
                        mention = StoryMention(user=user_info, x=0.5, y=0.7, width=0.3, height=0.1)
                        
                        # 4. Subir la historia a nuestra cuenta
                        print(f"Subiendo a nuestra historia y etiquetando a @{user_info.username}...")
                        if path_str.lower().endswith((".mp4", ".mov")):
                            cl.video_upload_to_story(path, mentions=[mention])
                        else:
                            cl.photo_upload_to_story(path, mentions=[mention])
                            
                        # Limpiar el archivo descargado
                        try:
                            import pathlib
                            if isinstance(path, pathlib.Path):
                                if path.exists():
                                    path.unlink()
                            elif os.path.exists(path_str):
                                os.remove(path_str)
                        except Exception as path_err:
                            print(f"Aviso: No se pudo eliminar el archivo temporal: {path_err}")
                            
                        # Registrar ID
                        reposted_ids.add(media_id)
                        with open(history_file, "a") as f:
                            f.write(f"{media_id}\n")
                            
                        print(f"{COLOR_GREEN}¡Mención repostada con éxito!{COLOR_RESET}")
                        reposted_any = True
                        
                    except Exception as e:
                        print(f"{COLOR_RED}Error al procesar la mención {media_id}: {e}{COLOR_RESET}")
                        
        if not reposted_any:
            print("No se encontraron menciones nuevas para repostear.")
            
    except Exception as e:
        print(f"{COLOR_RED}Error al buscar menciones: {str(e)}{COLOR_RESET}")


# --- CHAT INTERACTIVO (MODO ANTERIOR) ---

def run_chat_interface():
    # Verificar si está la API Key de Gemini
    if not os.environ.get("GEMINI_API_KEY"):
        print(f"\n{COLOR_BOLD}{COLOR_RED}ERROR: No se encontró la variable de entorno GEMINI_API_KEY.{COLOR_RESET}")
        print("Para usar tu agente de IA, necesitas una API Key de Gemini.")
        print("\nSigue estos pasos:")
        print("1. Obtén una API Key gratis en: https://aistudio.google.com/")
        print("2. Configúrala en tu archivo .env local.")
        sys.exit(1)

    print(f"\n{COLOR_BOLD}{COLOR_GREEN}=== Inicializando Agente de Clima con Gemini IA ==={COLOR_RESET}")
    try:
        client = genai.Client()
        chat = client.chats.create(
            model="gemini-3.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Eres un simpático y experto Agente de Clima de IA. "
                    "Tienes acceso a la herramienta 'get_current_weather' para consultar datos reales del clima. "
                    "Cuando el usuario te pregunte por el clima de una ciudad (de forma explícita o implícita), "
                    "DEBES llamar a la herramienta 'get_current_weather'. "
                    "Luego, redacta una respuesta conversacional, entretenida y útil para el usuario basada en esos datos. "
                    "Si hace frío, sugiérele abrigarse o tomar algo caliente. Si hace calor, recuérdale hidratarse. "
                    "Si va a llover, adviértele que lleve paraguas. "
                    "Mantén un tono amigable, ingenioso y de apoyo. Usa emojis. "
                    "Responde siempre en español."
                ),
                tools=[get_current_weather]
            )
        )
    except Exception as e:
        print(f"{COLOR_RED}Error al iniciar el cliente de Gemini: {str(e)}{COLOR_RESET}")
        sys.exit(1)

    prefix = f"{COLOR_BOLD}{COLOR_MAGENTA}[Agente de Clima (IA)]:{COLOR_RESET} {COLOR_CYAN}"
    print(f"{prefix}¡Hola! Soy tu agente del clima de IA. Pregúntame sobre el clima de cualquier ciudad o pídeme consejos. (Escribe 'salir' para terminar).{COLOR_RESET}")
    
    while True:
        try:
            user_input = input(f"\n{COLOR_BOLD}Tú > {COLOR_RESET}").strip()
            if not user_input:
                continue
            if user_input.lower() in ["salir", "exit", "quit"]:
                print(f"{prefix}¡Hasta luego! Cuídate y que tengas un excelente día.{COLOR_RESET}")
                break
            
            print(f"{COLOR_CYAN}Pensando...{COLOR_RESET}", end="\r")
            response = chat.send_message(user_input)
            print(" " * 15, end="\r")
            print(f"{prefix}{response.text}{COLOR_RESET}")
            
        except (KeyboardInterrupt, EOFError):
            print(f"\n{prefix}¡Hasta luego! Cuídate y que tengas un excelente día.{COLOR_RESET}")
            break
        except Exception as e:
            print(f"{COLOR_RED}Error al procesar solicitud: {str(e)}{COLOR_RESET}")

# --- ENTRADA PRINCIPAL ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente de IA y Automatizador de Instagram para @gravitymallsport")
    parser.add_argument("--share-story", action="store_true", help="Busca el Reel más antiguo no compartido y lo sube a Historias")
    parser.add_argument("--reply-dms", action="store_true", help="Revisa DMs no leídos y les responde usando Gemini")
    parser.add_argument("--metrics-report", action="store_true", help="Obtiene métricas de Instagram y escribe un reporte semanal en Markdown")
    parser.add_argument("--repost-mentions", action="store_true", help="Busca historias donde nos mencionaron y las comparte en las nuestras")
    parser.add_argument("--dry-run", action="store_true", help="Simula las acciones de Instagram sin conectarse realmente")
    
    args = parser.parse_args()
    
    if args.share_story:
        share_reels_to_stories(args.dry_run)
    elif args.reply_dms:
        reply_dms(args.dry_run)
    elif args.metrics_report:
        generate_weekly_report(args.dry_run)
    elif args.repost_mentions:
        repost_mentions(args.dry_run)
    else:
        run_chat_interface()
