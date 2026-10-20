pluginManagement {
    repositories {
        google()
        // Google's mirror of Maven Central: the central host rate-limits shared build machines.
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        // Google's mirror of Maven Central: the central host rate-limits shared build machines.
        maven("https://maven-central.storage-download.googleapis.com/maven2/")
        mavenCentral()
    }
}
rootProject.name = "aside-tv"
include(":app")
