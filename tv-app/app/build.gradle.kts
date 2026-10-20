plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.jannetekka.aside"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.jannetekka.aside"
        minSdk = 22          // Fire OS 5 and newer
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        buildConfigField("String", "ASIDE_URL", "\"${project.findProperty("asideUrl")}\"")
        buildConfigField("String", "ENDPOINT_URL", "\"https://raw.githubusercontent.com/JannetEkka/aside-tv/main/tv-app/endpoint.txt\"")
    }

    // One shared signing key, committed on purpose: every build (yours, CI, mine) can update the
    // app on the TV in place. It signs a sideloaded demo app only, never a store release.
    signingConfigs {
        create("sideload") {
            storeFile = file("../sideload.keystore")
            storePassword = "aside-sideload"
            keyAlias = "aside"
            keyPassword = "aside-sideload"
        }
    }
    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("sideload")
        }
        getByName("debug") {
            signingConfig = signingConfigs.getByName("sideload")
        }
    }
    buildFeatures { buildConfig = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}
