# Mobile release hardening (Android and iOS)

Read this when writing or reviewing native or cross-platform mobile code: storage, network, auth, release builds.

<!-- Distilled from OWASP MASVS/MASTG and the Mobile Top 10, ashishb/android-security-awesome, and ashishb/osx-and-ios-security-awesome. -->

- The app binary is public. Any key, endpoint secret, or signing material shipped in an APK/IPA is extractable in minutes — a client that needs a privileged API calls your backend, which holds the credential.
- Secrets and tokens live in the platform keystore (Android Keystore, iOS Keychain), never in `SharedPreferences`, `UserDefaults`, a plist, an SQLite row, or a file in app storage. Mark Keychain items with the strictest accessibility class the feature allows.
- Client-side controls — certificate pinning, root/jailbreak detection, tamper checks, obfuscation — are defense-in-depth that raises cost. Every security decision is re-made server-side, because instrumentation (Frida, a patched build) defeats the client by definition.
- Pin certificates with a documented rotation plan and a backup pin; a pin with no rotation path bricks the app on renewal day.
- Android: exported activities, services, receivers, and content providers validate the caller and the payload; deep links and app links verify the host and never trust an incoming URI as authorization. `android:allowBackup="false"` for anything holding user data.
- Cleartext traffic off by default (`usesCleartextTraffic="false"`, iOS App Transport Security left on); an exception is per-domain, documented, and never a blanket opt-out.
- Release builds enable code shrinking and obfuscation (R8/ProGuard) and strip debug logging — a `Log.d` of a token ships to logcat and to every app that can read it on older platforms.
- Sensitive screens block screenshots and the app-switcher snapshot where the platform supports it, and never place secrets on the clipboard.
- Biometric unlock gates a key in the keystore, not a boolean in app code — "if (biometricOk)" is patchable.
- WebViews load only trusted origins, keep JavaScript bridges minimal, and never expose a native method that takes a URL or file path from page content.
- Third-party SDKs are dependencies with device-level reach (`rules/dependencies.md`): review what each one collects and transmits before adding it.
- Ship a way to force-upgrade: a version floor checked server-side, so a client with a known-vulnerable build can be cut off.
