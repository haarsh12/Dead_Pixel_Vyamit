# How to Create Two Separate Apps for Two Different Backends

This guide will help you create two separate Flutter apps on your phone, each connecting to a different Render backend service.

## Overview

You have:
- **Backend 1**: `https://backend1.onrender.com` (example)
- **Backend 2**: `https://backend2.onrender.com` (example)

You need:
- **App 1**: "MyKirana Shop 1" connecting to Backend 1
- **App 2**: "MyKirana Shop 2" connecting to Backend 2

## Step-by-Step Guide

### 1. Create a Copy of Your Frontend Project

```bash
# From your workspace root
cp -r frontend_app frontend_app_shop2
```

Now you have:
- `frontend_app` → Will be App 1
- `frontend_app_shop2` → Will be App 2

---

### 2. Configure App 1 (frontend_app)

#### 2.1. Update Backend URL in `frontend_app/lib/core/config.dart`

```dart
class ApiConfig {
  // 🚀 PRODUCTION - Backend 1
  static const String _productionUrl = "https://your-backend-1.onrender.com";
  
  // Keep existing development URLs
  static const String _emulatorUrl = "http://10.0.2.2:8000";
  static const String _realDeviceUrl = "http://10.24.124.207:8000";
  static const String _localUrl = "http://localhost:8000";

  static String get baseUrl {
    if (kReleaseMode) {
      return _productionUrl;  // Use Backend 1 in release mode
    }
    
    if (Platform.isAndroid) {
      return _realDeviceUrl;
    }
    
    return _localUrl;
  }

  static String get wsUrl {
    final base = baseUrl;
    if (base.startsWith('https://')) {
      return base.replaceFirst('https://', 'wss://');
    }
    if (base.startsWith('http://')) {
      return base.replaceFirst('http://', 'ws://');
    }
    return 'ws://$base';
  }
}
```

#### 2.2. Update App Name in `frontend_app/pubspec.yaml`

```yaml
name: frontend_app
description: "MyKirana Shop 1"
publish_to: 'none'
version: 1.0.0+1
```

#### 2.3. Update Android Package ID in `frontend_app/android/app/build.gradle.kts`

```kotlin
android {
    namespace = "com.vyamit.mykirana.shop1"
    
    defaultConfig {
        applicationId = "com.vyamit.mykirana.shop1"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = 1
        versionName = "1.0.0"
    }
}
```

#### 2.4. Update App Label in `frontend_app/android/app/src/main/AndroidManifest.xml`

```xml
<application
    android:label="MyKirana Shop 1"
    android:name="${applicationName}"
    android:icon="@mipmap/ic_launcher">
```

---

### 3. Configure App 2 (frontend_app_shop2)

#### 3.1. Update Backend URL in `frontend_app_shop2/lib/core/config.dart`

```dart
class ApiConfig {
  // 🚀 PRODUCTION - Backend 2
  static const String _productionUrl = "https://your-backend-2.onrender.com";
  
  // Keep existing development URLs
  static const String _emulatorUrl = "http://10.0.2.2:8000";
  static const String _realDeviceUrl = "http://10.24.124.207:8000";
  static const String _localUrl = "http://localhost:8000";

  static String get baseUrl {
    if (kReleaseMode) {
      return _productionUrl;  // Use Backend 2 in release mode
    }
    
    if (Platform.isAndroid) {
      return _realDeviceUrl;
    }
    
    return _localUrl;
  }

  static String get wsUrl {
    final base = baseUrl;
    if (base.startsWith('https://')) {
      return base.replaceFirst('https://', 'wss://');
    }
    if (base.startsWith('http://')) {
      return base.replaceFirst('http://', 'ws://');
    }
    return 'ws://$base';
  }
}
```

#### 3.2. Update App Name in `frontend_app_shop2/pubspec.yaml`

```yaml
name: frontend_app_shop2
description: "MyKirana Shop 2"
publish_to: 'none'
version: 1.0.0+1
```

#### 3.3. Update Android Package ID in `frontend_app_shop2/android/app/build.gradle.kts`

```kotlin
android {
    namespace = "com.vyamit.mykirana.shop2"
    
    defaultConfig {
        applicationId = "com.vyamit.mykirana.shop2"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = 1
        versionName = "1.0.0"
    }
}
```

#### 3.4. Update App Label in `frontend_app_shop2/android/app/src/main/AndroidManifest.xml`

```xml
<application
    android:label="MyKirana Shop 2"
    android:name="${applicationName}"
    android:icon="@mipmap/ic_launcher">
```

#### 3.5. Update Kotlin Package in `frontend_app_shop2/android/app/src/main/kotlin/com/vyamit/mykirana/MainActivity.kt`

Rename the folder structure:
```
frontend_app_shop2/android/app/src/main/kotlin/com/vyamit/mykirana/shop2/MainActivity.kt
```

Update the package declaration:
```kotlin
package com.vyamit.mykirana.shop2

import io.flutter.embedding.android.FlutterActivity

class MainActivity: FlutterActivity() {
}
```

---

### 4. Build and Install Both Apps

#### 4.1. Build App 1

```bash
cd frontend_app
flutter clean
flutter pub get
flutter build apk --release
```

The APK will be at: `frontend_app/build/app/outputs/flutter-apk/app-release.apk`

#### 4.2. Build App 2

```bash
cd frontend_app_shop2
flutter clean
flutter pub get
flutter build apk --release
```

The APK will be at: `frontend_app_shop2/build/app/outputs/flutter-apk/app-release.apk`

#### 4.3. Install Both Apps on Your Phone

Transfer both APK files to your phone and install them. They will appear as:
- "MyKirana Shop 1" → connects to Backend 1
- "MyKirana Shop 2" → connects to Backend 2

---

## Summary of Key Changes

| Item | App 1 | App 2 |
|------|-------|-------|
| **Folder** | `frontend_app` | `frontend_app_shop2` |
| **Package Name** | `frontend_app` | `frontend_app_shop2` |
| **App Label** | "MyKirana Shop 1" | "MyKirana Shop 2" |
| **Application ID** | `com.vyamit.mykirana.shop1` | `com.vyamit.mykirana.shop2` |
| **Backend URL** | `https://your-backend-1.onrender.com` | `https://your-backend-2.onrender.com` |
| **Kotlin Package** | `com.vyamit.mykirana.shop1` | `com.vyamit.mykirana.shop2` |

---

## Important Notes

1. **Different Application IDs**: This is crucial - `com.vyamit.mykirana.shop1` and `com.vyamit.mykirana.shop2` must be different so Android treats them as separate apps.

2. **Separate Data**: Each app will have its own storage, so login sessions, preferences, and cached data won't conflict.

3. **Different Icons (Optional)**: You can create different launcher icons for each app by:
   - Replacing `assets/vyamitlogo.png` with different images in each project
   - Running `flutter pub run flutter_launcher_icons`

4. **Testing**: Before building release APKs, test each app in debug mode:
   ```bash
   cd frontend_app
   flutter run
   
   cd frontend_app_shop2
   flutter run
   ```

5. **Backend URLs**: Make sure to replace the example URLs with your actual Render backend URLs.

---

## Quick Reference Commands

```bash
# Build App 1
cd frontend_app
flutter build apk --release

# Build App 2
cd frontend_app_shop2
flutter build apk --release

# Install on connected phone
cd frontend_app
flutter install

cd frontend_app_shop2
flutter install
```

---

## Troubleshooting

**If apps won't install together:**
- Make sure Application IDs are different in both `build.gradle.kts` files
- Make sure Kotlin package paths are different

**If app connects to wrong backend:**
- Check `lib/core/config.dart` in each project
- Make sure you built release mode: `flutter build apk --release`

**If you get build errors:**
- Run `flutter clean` in each project
- Run `flutter pub get` in each project
- Check that all file paths are correct after copying
