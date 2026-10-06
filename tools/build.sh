#!/usr/bin/env bash
# Build helper for Pixel Fantasy Survival (Godot 4.5.2).
#
#   tools/build.sh test             # unit + smoke tests (headless)
#   tools/build.sh android-debug    # build/android/pixel-fantasy-survival-debug.apk
#   tools/build.sh android-release  # build/android/pixel-fantasy-survival.apk (needs release keystore env)
#   tools/build.sh ios              # build/ios/ Xcode project (needs IOS_TEAM_ID)
#
# Environment:
#   GODOT                                   path to the Godot 4.5.2 editor binary (default: godot)
#   GODOT_ANDROID_KEYSTORE_DEBUG_PATH       default: ~/.android/debug.keystore
#   GODOT_ANDROID_KEYSTORE_DEBUG_USER       default: androiddebugkey
#   GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD   default: android
#   GODOT_ANDROID_KEYSTORE_RELEASE_PATH / _USER / _PASSWORD   required for android-release
#   IOS_TEAM_ID                             Apple Developer Team ID, required for ios
#
# Android SDK / JDK 17 paths are taken from the Godot editor settings
# (Editor Settings -> Export -> Android) or set by CI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT="$ROOT/game"
BUILD="$ROOT/build"
GODOT="${GODOT:-godot}"
REQUIRED_VERSION="4.5.2.stable"

check_godot() {
  local version
  version="$("$GODOT" --version | head -n1)"
  if [[ "$version" != "$REQUIRED_VERSION"* ]]; then
    echo "error: Godot $REQUIRED_VERSION required, got '$version' ($GODOT)" >&2
    exit 1
  fi
}

import_project() {
  "$GODOT" --headless --path "$PROJECT" --import >/dev/null 2>&1 || true
}

run_tests() {
  "$GODOT" --headless --path "$PROJECT" res://tests/test_runner.tscn
}

android_debug() {
  export GODOT_ANDROID_KEYSTORE_DEBUG_PATH="${GODOT_ANDROID_KEYSTORE_DEBUG_PATH:-$HOME/.android/debug.keystore}"
  export GODOT_ANDROID_KEYSTORE_DEBUG_USER="${GODOT_ANDROID_KEYSTORE_DEBUG_USER:-androiddebugkey}"
  export GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD="${GODOT_ANDROID_KEYSTORE_DEBUG_PASSWORD:-android}"
  if [[ ! -f "$GODOT_ANDROID_KEYSTORE_DEBUG_PATH" ]]; then
    mkdir -p "$(dirname "$GODOT_ANDROID_KEYSTORE_DEBUG_PATH")"
    keytool -genkeypair -v -keystore "$GODOT_ANDROID_KEYSTORE_DEBUG_PATH" -storepass android -keypass android \
      -alias androiddebugkey -dname "CN=Android Debug,O=Android,C=US" -keyalg RSA -keysize 2048 -validity 10000
  fi
  mkdir -p "$BUILD/android"
  "$GODOT" --headless --path "$PROJECT" --export-debug "Android" "$BUILD/android/pixel-fantasy-survival-debug.apk"
  ls -lh "$BUILD/android/pixel-fantasy-survival-debug.apk"
}

android_release() {
  : "${GODOT_ANDROID_KEYSTORE_RELEASE_PATH:?set GODOT_ANDROID_KEYSTORE_RELEASE_PATH}"
  : "${GODOT_ANDROID_KEYSTORE_RELEASE_USER:?set GODOT_ANDROID_KEYSTORE_RELEASE_USER}"
  : "${GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD:?set GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD}"
  mkdir -p "$BUILD/android"
  "$GODOT" --headless --path "$PROJECT" --export-release "Android" "$BUILD/android/pixel-fantasy-survival.apk"
  ls -lh "$BUILD/android/pixel-fantasy-survival.apk"
}

ios() {
  : "${IOS_TEAM_ID:?set IOS_TEAM_ID (Apple Developer Team ID)}"
  # The team ID is written into the presets only for the duration of the export, so it never lands in git.
  local presets="$PROJECT/export_presets.cfg"
  cp "$presets" "$presets.bak"
  # Expanded now: the local variable no longer exists when the EXIT trap runs.
  trap "mv '$presets.bak' '$presets'" EXIT
  sed -i.tmp "s/^application\/app_store_team_id=\"\"/application\/app_store_team_id=\"$IOS_TEAM_ID\"/" "$presets" && rm -f "$presets.tmp"
  mkdir -p "$BUILD/ios"
  "$GODOT" --headless --path "$PROJECT" --export-release "iOS" "$BUILD/ios/PixelFantasySurvival.ipa"
  echo "Xcode project: $BUILD/ios/PixelFantasySurvival.xcodeproj (open in Xcode to sign, archive and upload)"
}

check_godot
import_project
case "${1:-}" in
  test) run_tests ;;
  android-debug) android_debug ;;
  android-release) android_release ;;
  ios) ios ;;
  *) sed -n '2,20p' "$0"; exit 1 ;;
esac
