[app]

title = Dacla
package.name = dacla
package.domain = org.dacla
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,md
requirements = python3,kivy,requests,pyjnius,android
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,RECORD_AUDIO
android.api = 34
android.minapi = 24
android.ndk = 25b
android.sdk = 34
android.archs = arm64-v8a, armeabi-v7a
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
