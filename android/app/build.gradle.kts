import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.chaquo.python")
}

val repoRoot = rootProject.projectDir.parentFile
val stagedPythonDir = layout.buildDirectory.dir("staged-python")

android {
    namespace = "com.tgchatmonitor.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.tgchatmonitor.app"
        minSdk = 26
        targetSdk = 35
        versionCode = 9
        versionName = "1.0.9"

        ndk {
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    signingConfigs {
        create("release") {
            val props = Properties()
            val localProps = rootProject.file("local.properties")
            if (localProps.exists()) {
                localProps.inputStream().use { props.load(it) }
            }

            val storeFilePath = System.getenv("KEYSTORE_PATH")
                ?: props.getProperty("KEYSTORE_PATH")
            val storePasswordValue = System.getenv("KEYSTORE_PASSWORD")
                ?: props.getProperty("KEYSTORE_PASSWORD")
            val keyAliasValue = System.getenv("KEY_ALIAS")
                ?: props.getProperty("KEY_ALIAS")
            val keyPasswordValue = System.getenv("KEY_PASSWORD")
                ?: props.getProperty("KEY_PASSWORD")

            if (storeFilePath != null && storePasswordValue != null &&
                keyAliasValue != null && keyPasswordValue != null
            ) {
                storeFile = file(storeFilePath)
                storePassword = storePasswordValue
                keyAlias = keyAliasValue
                keyPassword = keyPasswordValue
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            val releaseSigning = signingConfigs.getByName("release")
            if (releaseSigning.storeFile != null) {
                signingConfig = releaseSigning
            }
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

chaquopy {
    defaultConfig {
        // 3.13: better Android wheel coverage for native deps (aiohttp, etc.).
        version = "3.13"
        pip {
            // pyaes (sdist-only on PyPI) + pydantic-core (Rust) live in android/wheels.
            options(
                "--find-links",
                rootProject.file("wheels").absolutePath,
            )
            install("-r", rootProject.file("requirements-android.txt").absolutePath)
        }
    }
    sourceSets {
        getByName("main") {
            setSrcDirs(listOf(stagedPythonDir.get().asFile.path))
        }
    }
}

val stagePythonSources by tasks.registering(Copy::class) {
    description = "Copy Python app sources into Chaquopy source set"
    into(stagedPythonDir)

    from(repoRoot) {
        include("*.py")
        exclude("setup.py")
    }
    from(repoRoot.resolve("handlers")) {
        into("handlers")
        include("**/*.py")
    }
    from(repoRoot.resolve("services")) {
        into("services")
        include("**/*.py")
    }
}

tasks.named("preBuild") {
    dependsOn(stagePythonSources)
}

afterEvaluate {
    tasks.matching {
        it.name.contains("Python", ignoreCase = true) &&
            (it.name.startsWith("extract") || it.name.startsWith("merge") ||
                it.name.startsWith("generate") || it.name.startsWith("compile"))
    }.configureEach {
        dependsOn(stagePythonSources)
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    androidTestImplementation(composeBom)

    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    // Explicit Android artifacts: Chaquopy + KMP metadata can leave
    // plain "ui"/"foundation" without Modifier on the compile classpath.
    implementation("androidx.compose.ui:ui-android")
    implementation("androidx.compose.ui:ui-tooling-preview-android")
    implementation("androidx.compose.foundation:foundation-android")
    implementation("androidx.compose.material3:material3-android")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("com.google.android.material:material:1.12.0")

    debugImplementation("androidx.compose.ui:ui-tooling")
}
