[app]

# App title
title = MeshPhone

# Package name
package.name = meshphone

# Package domain (reversed)
package.domain = org.meshphone

# Source code directory
source.dir = .

# Source files to include
source.include_exts = py,png,jpg,kv,atlas

# App version
version = 0.1.0

# App requirements (Python packages)
requirements = python3,kivy,cryptography,setuptools

# App permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,BLUETOOTH,BLUETOOTH_ADMIN,ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION

# Android API level
android.api = 31

# Minimum API level
android.minapi = 21

# Android NDK version
android.ndk = 25b

# Android SDK version
android.sdk = 31

# Orientation
orientation = portrait

# Fullscreen
fullscreen = 0

# Presplash background color
presplash.color = #000000

# Icon (will use default if not specified)
#icon.filename = %(source.dir)s/icon.png

# Presplash image
#presplash.filename = %(source.dir)s/presplash.png

# Android architecture
android.archs = arm64-v8a,armeabi-v7a

[buildozer]

# Log level (0 = error, 1 = info, 2 = debug)
log_level = 2

# Display warning if buildozer is run as root
warn_on_root = 1

# Build directory
build_dir = ./.buildozer

# Bin directory
bin_dir = ./bin
