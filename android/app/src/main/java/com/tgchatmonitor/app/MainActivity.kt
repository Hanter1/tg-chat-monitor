package com.tgchatmonitor.app

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.getSystemService
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.chaquo.python.Python
import kotlinx.coroutines.delay

class MainActivity : ComponentActivity() {
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { /* no-op */ }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }

        setContent {
            MaterialTheme(colorScheme = darkColorScheme()) {
                AppScreen(
                    dataDir = filesDir,
                    onStart = { MonitorService.start(this) },
                    onStop = { MonitorService.stop(this) },
                    onSubmitAuth = { MonitorService.submitAuth(this, it) },
                    onOpenBatterySettings = { openBatterySettings() },
                    authBrokerProvider = { MonitorService.instanceAuthBroker },
                    serviceRunningProvider = { MonitorService.isRunning },
                    statusProvider = {
                        if (!Python.isStarted()) {
                            "idle"
                        } else {
                            try {
                                Python.getInstance()
                                    .getModule("android_bridge")
                                    .callAttr("get_status")
                                    .toString()
                            } catch (_: Exception) {
                                if (MonitorService.isRunning) "starting" else "idle"
                            }
                        }
                    },
                    errorProvider = {
                        try {
                            Python.getInstance()
                                .getModule("android_bridge")
                                .callAttr("get_last_error")
                                .toString()
                        } catch (_: Exception) {
                            ""
                        }
                    },
                )
            }
        }
    }

    private fun openBatterySettings() {
        val pm = getSystemService<PowerManager>()
        if (pm != null && !pm.isIgnoringBatteryOptimizations(packageName)) {
            startActivity(
                Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS).apply {
                    data = Uri.parse("package:$packageName")
                },
            )
        } else {
            startActivity(Intent(Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS))
        }
    }
}

@Composable
private fun AppScreen(
    dataDir: java.io.File,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onSubmitAuth: (String) -> Unit,
    onOpenBatterySettings: () -> Unit,
    authBrokerProvider: () -> AuthBroker?,
    serviceRunningProvider: () -> Boolean,
    statusProvider: () -> String,
    errorProvider: () -> String,
) {
    var tab by remember { mutableStateOf(0) }
    var values by remember { mutableStateOf(EnvStore.load(dataDir)) }
    var savedMessage by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("idle") }
    var error by remember { mutableStateOf("") }
    var serviceRunning by remember { mutableStateOf(false) }
    var authKind by remember { mutableStateOf(AuthBroker.PromptKind.NONE) }
    var authInput by remember { mutableStateOf("") }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                values = EnvStore.load(dataDir)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    LaunchedEffect(Unit) {
        while (true) {
            status = statusProvider()
            error = errorProvider()
            serviceRunning = serviceRunningProvider()
            authKind = authBrokerProvider()?.pendingKind ?: AuthBroker.PromptKind.NONE
            delay(800)
        }
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("TG Chat Monitor", style = MaterialTheme.typography.headlineMedium)
            Text(
                "Мониторинг чатов на телефоне. Управление — через Telegram-бота.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (tab == 0) {
                    Button(onClick = { tab = 0 }) { Text("Статус") }
                } else {
                    OutlinedButton(onClick = { tab = 0 }) { Text("Статус") }
                }
                if (tab == 1) {
                    Button(onClick = { tab = 1 }) { Text("Настройки") }
                } else {
                    OutlinedButton(onClick = { tab = 1 }) { Text("Настройки") }
                }
            }

            if (tab == 0) {
                StatusCard(
                    status = status,
                    error = error,
                    serviceRunning = serviceRunning,
                    configured = EnvStore.isConfigured(dataDir),
                    onStart = {
                        if (!EnvStore.isConfigured(dataDir)) {
                            tab = 1
                            savedMessage = "Сначала заполните настройки"
                        } else {
                            onStart()
                        }
                    },
                    onStop = onStop,
                    onOpenBatterySettings = onOpenBatterySettings,
                )

                if (authKind != AuthBroker.PromptKind.NONE) {
                    AuthCard(
                        kind = authKind,
                        value = authInput,
                        onValueChange = { authInput = it },
                        onSubmit = {
                            onSubmitAuth(authInput)
                            authInput = ""
                        },
                    )
                }
            } else {
                SettingsForm(
                    values = values,
                    message = savedMessage,
                    onChange = { key, value -> values = values.toMutableMap().also { it[key] = value } },
                    onSave = {
                        EnvStore.save(dataDir, values)
                        savedMessage = "Сохранено"
                    },
                )
            }
        }
    }
}

@Composable
private fun StatusCard(
    status: String,
    error: String,
    serviceRunning: Boolean,
    configured: Boolean,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onOpenBatterySettings: () -> Unit,
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Статус: $status", style = MaterialTheme.typography.titleMedium)
            Text(if (configured) "Настройки: OK" else "Настройки: не заполнены")
            Text(if (serviceRunning) "Сервис: работает" else "Сервис: остановлен")
            if (error.isNotBlank()) {
                Text("Ошибка: $error", color = MaterialTheme.colorScheme.error)
            }
            Spacer(Modifier.height(4.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onStart, enabled = !serviceRunning) { Text("Старт") }
                OutlinedButton(onClick = onStop, enabled = serviceRunning) { Text("Стоп") }
            }
            TextButton(onClick = onOpenBatterySettings) {
                Text("Исключить из оптимизации батареи")
            }
            Text(
                "Совет: на Xiaomi/Huawei/Samsung разрешите автозапуск, иначе Android убьёт фон.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun AuthCard(
    kind: AuthBroker.PromptKind,
    value: String,
    onValueChange: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    val title = when (kind) {
        AuthBroker.PromptKind.PHONE -> "Номер телефона (+7…)"
        AuthBroker.PromptKind.CODE -> "Код из Telegram"
        AuthBroker.PromptKind.PASSWORD -> "Пароль 2FA"
        AuthBroker.PromptKind.NONE -> return
    }
    val isPassword = kind == AuthBroker.PromptKind.PASSWORD
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("Вход Telethon", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                value = value,
                onValueChange = onValueChange,
                label = { Text(title) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                visualTransformation = if (isPassword) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
                keyboardOptions = KeyboardOptions(
                    keyboardType = when (kind) {
                        AuthBroker.PromptKind.PHONE -> KeyboardType.Phone
                        AuthBroker.PromptKind.CODE -> KeyboardType.Number
                        else -> KeyboardType.Password
                    },
                ),
            )
            Button(onClick = onSubmit, enabled = value.isNotBlank()) { Text("Отправить") }
        }
    }
}

@Composable
private fun SettingsForm(
    values: Map<String, String>,
    message: String,
    onChange: (String, String) -> Unit,
    onSave: () -> Unit,
) {
    val fields = listOf(
        "BOT_TOKEN" to "Токен бота",
        "API_ID" to "API ID",
        "API_HASH" to "API Hash",
        "ADMIN_USER_ID" to "Admin User ID",
        "POLL_INTERVAL" to "Интервал опроса (сек)",
    )
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        fields.forEach { (key, label) ->
            OutlinedTextField(
                value = values[key].orEmpty(),
                onValueChange = { onChange(key, it) },
                label = { Text(label) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                visualTransformation = if (key.contains("TOKEN") || key.contains("HASH")) {
                    PasswordVisualTransformation()
                } else {
                    androidx.compose.ui.text.input.VisualTransformation.None
                },
            )
        }
        Button(onClick = onSave, modifier = Modifier.fillMaxWidth()) { Text("Сохранить") }
        if (message.isNotBlank()) {
            Text(message, color = MaterialTheme.colorScheme.primary)
        }
    }
}
