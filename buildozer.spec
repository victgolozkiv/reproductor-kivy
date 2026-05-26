[app]

# (str) Title of your application
title = golomn

# (str) Package name
package.name = musicplayeryt

# (str) Package domain (needed for android/ios packaging)
package.domain = org.test

# (str) Application version
version = 0.1

# (bool) Auto-accept SDK license
android.accept_sdk_license = True

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) Application requirements
# comma separated e.g. requirements = sqlite3,kivy
requirements = python3, kivy==2.3.0, kivymd==1.2.0, yt-dlp, pillow, openssl, certifi, requests, urllib3, charset-normalizer, idna, android, pyjnius, setuptools

# (str) Custom source folders for requirements
# packgage.setup_py = 

# (list) Garden requirements
#garden_requirements =

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
#icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait or all)
orientation = portrait

# (list) Permissions
android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE, WAKE_LOCK, READ_MEDIA_AUDIO, ACCESS_NETWORK_STATE, POST_NOTIFICATIONS, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MEDIA_PLAYBACK, MANAGE_EXTERNAL_STORAGE

# (int) Android API to use
android.api = 33

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (int) Minimum API your APK will support.
android.minapi = 21

# (str) Android NDK version to use
#android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (list) Android additionnal libraries for substitution
#android.add_libs_armeabi_v7a = libs/armeabi-v7a/libvlc.so

# (bool) Indicate whether the screen should stay on
# android.wakelock = True

# (list) The Android archs to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

# (bool) enables Android auto backup feature (Android API >= 23)
android.allow_backup = True
p4a.branch = master

# (list) Android services to declare
services = playback:service.py

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, second part is default
# build_dir = ./.buildozer

# (str) Path to build output (after android dump)
# bin_dir = ./bin
