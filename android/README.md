# Varjoaika Android widget

Native Java / Android RemoteViews widget, minimum Android 6.0 (API 23), target API 36.
Uses no Python runtime, native binaries, advertising, Internet permission or background
service. TextClock updates the time through Android. The phone must have automatic
time enabled; this Android edition does not schedule MIKES NTP requests.

Install the APK, open Varjoaika once, then long-press an empty area of your home screen
and choose Widgets → Varjoaika. Tap the widget for its dark settings screen.
Adjust clock/date/year/official-date sizes, text opacity, font family and seconds.
Settings affect all instances. Drag/resize using your launcher's normal controls.
The launcher decides placement and may supply its own padding; background is transparent.

Date arithmetic matches the desktop anchor: 2026-10-04 = 0001-00-06.
Seven gothic weekdays, 13 numbered months and 30 numbered days per month.
The official Finnish date appears without a time at the bottom.

Dates update on widget refresh (30 minutes), time/timezone changes and an inexact
midnight alarm. Android Doze and manufacturer battery policies can delay date refresh.
Tap the widget and choose Päivitä päivämäärä nyt if needed. Force-stopped apps
need to be opened again. Clock ticks are rendered by Android's TextClock.

The initial GitHub APK is a **debug-signed test build**, not a Play Store production
release. CI debug signing keys may differ between builds; a later test APK may require
uninstalling the previous APK first, which resets widget settings. Stable production
signing should be configured before wider distribution. No physical-device testing
is claimed, and compatibility with every Android version/launcher is not guaranteed.

Build using JDK 17, Android SDK 36, build-tools 35.0.0 and Gradle 8.13:
`gradle --no-daemon testDebugUnitTest lintDebug assembleDebug`
Open this folder in Android Studio or run the GitHub Actions release workflow.
Original code MIT; Android platform and build-tool dependencies retain their licenses.
