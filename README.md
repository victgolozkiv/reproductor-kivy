# 🌌 Reproductor AMOLED - Purple Neon Edition 💜

Un reproductor de música minimalista, elegante y ergonómico diseñado para dispositivos móviles con pantallas AMOLED (optimizado para **POCO M7 Pro**).

![Reproductor AMOLED](https://img.shields.io/badge/Status-Desarrollo-blueviolet?style=for-the-badge)
![Kivy](https://img.shields.io/badge/Built%20with-Kivy-blue?style=for-the-badge)
![AMOLED](https://img.shields.io/badge/Optimized%20for-AMOLED-black?style=for-the-badge)

## ✨ Características Principales
- **Fondo Negro Puro (#000000)**: Ahorro máximo de batería en pantallas AMOLED.
- **Neon Breathing Effect**: Títulos y carátulas con animaciones de pulso y brillo sincronizadas.
- **Navegación Circular**: Reproducción infinita sin errores al final de la lista.
- **Descargas Offline**: Guarda tus canciones favoritas directamente en tu dispositivo.
- **Búsqueda Inteligente**: Integración con YouTube mediante `yt-dlp`.
- **Modos Avanzados**: Shuffle (aleatorio) y Repeat (repetición) integrados.

## 🚀 Instalación (Desarrollo)
1. Clona el repositorio:
   ```bash
   git clone https://github.com/TU_USUARIO/reproductor-kivy.git
   cd reproductor-kivy
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Ejecuta la aplicación:
   ```bash
   python main.py
   ```

## 📱 Compilación e Instalación en Android
Este proyecto utiliza `buildozer` (probado en Android 14 / API 34).

### Opción 1: Instalación Automática por USB (Recomendada)
Si tienes tu celular conectado por USB con la **Depuración USB** activada, puedes compilar, instalar y ejecutar la app en un solo comando:
```bash
buildozer android debug deploy run
```
*(Nota: Si hiciste cambios importantes, usa `buildozer android clean && buildozer android debug deploy run`)*

### Opción 2: Instalación Manual del APK
Si solo quieres generar el archivo para pasarlo a tu celular después:
1. Ejecuta la compilación básica:
   ```bash
   buildozer -v android debug
   ```
2. Una vez que termine (puede tardar de 15 a 30 minutos la primera vez), el archivo `.apk` final aparecerá dentro de la carpeta oculta `bin/` en el directorio de tu proyecto.
3. Pasa ese archivo `.apk` a tu celular (por Bluetooth, Telegram, o cable) e instálalo normalmente. Acuérdate de concederle el permiso de instalar aplicaciones de orígenes desconocidos.

### Opción 3: Descarga Directa (Para Usuarios Finales)
Si no eres desarrollador y solo quieres probar el reproductor en tu celular:
1. Ve a la pestaña de **[Releases]** (Lanzamientos) de este repositorio en GitHub desde tu celular.
2. Descarga el archivo `.apk` más reciente.
3. Al abrirlo, tu celular te pedirá permiso para instalar aplicaciones de **Orígenes Desconocidos**. Dale en Aceptar.
4. Al abrir la app por primera vez, asegúrate de otorgar los permisos de "Almacenamiento" y "Mostrar Notificaciones" (esto es indispensable para que las portadas y descargas funcionen correctamente en segundo plano).

## 🛡️ Privacidad y Seguridad
Esta aplicación fue diseñada con la privacidad del usuario y la transparencia como prioridad absoluta:
- **Cero Rastreo (Telemetry-Free):** No incluye anuncios, SDKs de rastreo (como Google Analytics o Facebook Ads) ni recopilación de datos en segundo plano.
- **Conexiones Directas:** Las descargas y el streaming de audio se realizan conectándose directa y únicamente a los servidores oficiales mediante `yt-dlp` a través de conexiones cifradas (HTTPS).
- **Permisos Éticos:** La app solicita estrictamente los permisos indispensables para funcionar (Almacenamiento para guardar tus canciones mp3 locales y Notificaciones para el control del reproductor en la pantalla de bloqueo). **No** accede a tus contactos, cámara, micrófono ni ubicación.
- **Código Abierto:** Eres libre de auditar y revisar línea por línea el código fuente en este repositorio para confirmar su integridad.

## 💖 Soporte y Donaciones
Si te gusta este proyecto y quieres apoyar mi trabajo (¡incluso 1 peso ayuda! ), puedes hacerlo a través de PayPal:

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?style=for-the-badge&logo=paypal)](https://www.paypal.com/paypalme/VictorRicardo162/1)



---
Desarrollado con ❤️ por victor.
esto se hizo la mayoria con IA 
lo creee para una sulucion por un problema que tenia por que cuando me iva de con mi novia queria irme escuhando musica en el carro jaj no encotraba ningun reproductor que me diera esto sin anuncios y que fuera bonito y que funcionara bien y gratis 
y que me permitiera descargar canciones sin limitaciones casi todo fue por esto por querer descargar las canciones gratis antes usaba snaptube pero tiene demasiados anuncios y dicen que es muy inseguro. 
espero les guste este proyecto lo hice  todo con IA antigravty y voy a seguir mejorando y el que quiera ayudar a mejorarlo adelante 