package com.tgchatmonitor.app.ui

import android.content.ClipboardManager
import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.OpenInNew
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.Chat
import androidx.compose.material.icons.outlined.ContentPaste
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.Home
import androidx.compose.material.icons.outlined.Key
import androidx.compose.material.icons.outlined.OpenInBrowser
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material.icons.outlined.Visibility
import androidx.compose.material.icons.outlined.VisibilityOff
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.core.content.getSystemService
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.tgchatmonitor.app.AuthBroker
import com.tgchatmonitor.app.CredentialsHelper
import com.tgchatmonitor.app.EnvStore
import com.tgchatmonitor.app.PythonBridge
import com.tgchatmonitor.app.R
import com.tgchatmonitor.app.ui.theme.Accent
import com.tgchatmonitor.app.ui.theme.Danger
import com.tgchatmonitor.app.ui.theme.OnMuted
import com.tgchatmonitor.app.ui.theme.OnSurface
import com.tgchatmonitor.app.ui.theme.SlateBg
import com.tgchatmonitor.app.ui.theme.SlateElevated
import com.tgchatmonitor.app.ui.theme.SlateSurface
import com.tgchatmonitor.app.ui.theme.Success
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

enum class AppTab { Home, Chats, Words, Matches, More }

@Composable
fun AppRoot(
    dataDir: File,
    onStartService: () -> Unit,
    onStopService: () -> Unit,
    onSubmitAuth: (String) -> Unit,
    onOpenBatterySettings: () -> Unit,
    authBrokerProvider: () -> AuthBroker?,
    serviceRunningProvider: () -> Boolean,
    bridgeProvider: () -> PythonBridge?,
    statusProvider: () -> String,
    errorProvider: () -> String,
) {
    var tab by remember { mutableStateOf(AppTab.Home) }
    var status by remember { mutableStateOf("idle") }
    var error by remember { mutableStateOf("") }
    var serviceRunning by remember { mutableStateOf(false) }
    var configured by remember { mutableStateOf(EnvStore.isConfigured(dataDir)) }
    var authKind by remember { mutableStateOf(AuthBroker.PromptKind.NONE) }
    var flash by remember { mutableStateOf<String?>(null) }

    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                configured = EnvStore.isConfigured(dataDir)
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
            delay(700)
        }
    }

    LaunchedEffect(flash) {
        if (flash != null) {
            delay(2800)
            flash = null
        }
    }

    val runtimeReady = status == "running"

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    listOf(Color(0xFF0E1830), SlateBg, Color(0xFF081018)),
                ),
            ),
    ) {
        Scaffold(
            containerColor = Color.Transparent,
            bottomBar = {
                if (configured) {
                    NavigationBar(containerColor = SlateSurface.copy(alpha = 0.96f)) {
                        val items = listOf(
                            AppTab.Home to Icons.Outlined.Home,
                            AppTab.Chats to Icons.Outlined.Chat,
                            AppTab.Words to Icons.Outlined.Key,
                            AppTab.Matches to Icons.Outlined.History,
                            AppTab.More to Icons.Outlined.Tune,
                        )
                        items.forEach { (t, icon) ->
                            NavigationBarItem(
                                selected = tab == t,
                                onClick = { tab = t },
                                icon = { Icon(icon, contentDescription = t.name) },
                                label = {
                                    Text(
                                        when (t) {
                                            AppTab.Home -> "Главная"
                                            AppTab.Chats -> "Чаты"
                                            AppTab.Words -> "Слова"
                                            AppTab.Matches -> "Журнал"
                                            AppTab.More -> "Ещё"
                                        },
                                    )
                                },
                                colors = NavigationBarItemDefaults.colors(
                                    selectedIconColor = Accent,
                                    selectedTextColor = Accent,
                                    indicatorColor = SlateElevated,
                                    unselectedIconColor = OnMuted,
                                    unselectedTextColor = OnMuted,
                                ),
                            )
                        }
                    }
                }
            },
        ) { padding ->
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .padding(horizontal = 16.dp),
            ) {
                Spacer(Modifier.height(12.dp))
                BrandHeader(
                    status = resolveServiceStatus(status, serviceRunning, runtimeReady),
                )
                Spacer(Modifier.height(12.dp))

                AnimatedVisibility(visible = flash != null, enter = fadeIn(), exit = fadeOut()) {
                    Text(
                        flash.orEmpty(),
                        color = Success,
                        style = MaterialTheme.typography.bodyMedium,
                        modifier = Modifier.padding(bottom = 8.dp),
                    )
                }

                if (!configured) {
                    OnboardingSettings(
                        dataDir = dataDir,
                        onSaved = {
                            configured = true
                            flash = "Настройки сохранены"
                        },
                    )
                } else {
                    when (tab) {
                        AppTab.Home -> HomePane(
                            status = status,
                            error = error,
                            serviceRunning = serviceRunning,
                            runtimeReady = runtimeReady,
                            authKind = authKind,
                            bridgeProvider = bridgeProvider,
                            onStartService = onStartService,
                            onStopService = onStopService,
                            onSubmitAuth = onSubmitAuth,
                            onOpenBatterySettings = onOpenBatterySettings,
                            onFlash = { flash = it },
                            onNeedSettings = { tab = AppTab.More },
                        )
                        AppTab.Chats -> ChatsPane(
                            runtimeReady = runtimeReady,
                            bridgeProvider = bridgeProvider,
                            onFlash = { flash = it },
                        )
                        AppTab.Words -> WordsPane(
                            runtimeReady = runtimeReady,
                            bridgeProvider = bridgeProvider,
                            onFlash = { flash = it },
                        )
                        AppTab.Matches -> MatchesPane(
                            runtimeReady = runtimeReady,
                            bridgeProvider = bridgeProvider,
                        )
                        AppTab.More -> MorePane(
                            dataDir = dataDir,
                            runtimeReady = runtimeReady,
                            bridgeProvider = bridgeProvider,
                            onFlash = { flash = it },
                            onOpenBatterySettings = onOpenBatterySettings,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun BrandHeader(status: StatusInfo) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Image(
            painter = painterResource(R.drawable.ic_launcher_fg),
            contentDescription = null,
            modifier = Modifier
                .size(48.dp)
                .clip(RoundedCornerShape(14.dp))
                .border(1.dp, Accent.copy(alpha = 0.35f), RoundedCornerShape(14.dp)),
            contentScale = ContentScale.Crop,
        )
        Spacer(Modifier.width(12.dp))
        Column {
            Text(
                "TG Chat Monitor",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = OnSurface,
            )
            Spacer(Modifier.height(6.dp))
            StatusBadge(status)
        }
    }
}

@Composable
private fun OnboardingSettings(dataDir: File, onSaved: () -> Unit) {
    val context = LocalContext.current
    var apiId by remember { mutableStateOf(EnvStore.load(dataDir)["API_ID"].orEmpty()) }
    var apiHash by remember { mutableStateOf(EnvStore.load(dataDir)["API_HASH"].orEmpty()) }
    var hint by remember { mutableStateOf<String?>(null) }
    val canContinue = apiId.isNotBlank() && apiHash.isNotBlank()

    fun openAppsPage() {
        context.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(CredentialsHelper.MY_TELEGRAM_APPS)),
        )
    }

    fun pasteFromClipboard() {
        val cm = context.getSystemService<ClipboardManager>()
        val text = cm?.primaryClip?.takeIf { it.itemCount > 0 }
            ?.getItemAt(0)?.coerceToText(context)?.toString().orEmpty()
        val parsed = CredentialsHelper.parse(text)
        if (!parsed.hasAnything) {
            hint = "В буфере нет API ID / Hash. Скопируйте их со страницы my.telegram.org"
            return
        }
        parsed.apiId?.let { apiId = it }
        parsed.apiHash?.let { apiHash = it }
        hint = when {
            parsed.apiId != null && parsed.apiHash != null -> "Готово: ID и Hash вставлены из буфера"
            parsed.apiId != null -> "API ID вставлен — скопируйте ещё Hash"
            else -> "API Hash вставлен — скопируйте ещё ID"
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Panel {
            Text("Быстрый старт", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Spacer(Modifier.height(6.dp))
            Text(
                "Нужны только API ID и API Hash. Бот не обязателен — уведомления приходят из приложения.",
                color = OnMuted,
            )
        }

        Panel {
            StepRow(1, "Откройте страницу Telegram API")
            Spacer(Modifier.height(10.dp))
            PrimaryButton(
                onClick = { openAppsPage() },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.OpenInBrowser, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Получить API ID и Hash", fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.height(8.dp))
            Text(
                "Войдите на my.telegram.org → Apps → создайте приложение, если ещё нет. " +
                    "Скопируйте App api_id и App api_hash.",
                color = OnMuted,
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        Panel {
            StepRow(2, "Вставьте данные в приложение")
            Spacer(Modifier.height(10.dp))
            SecondaryButton(
                onClick = { pasteFromClipboard() },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Outlined.ContentPaste, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Вставить из буфера")
            }
            Spacer(Modifier.height(12.dp))
            Field(
                label = "API ID",
                value = apiId,
                keyboardType = KeyboardType.Number,
                onPaste = {
                    val pasted = readClipboard(context)
                    val p = CredentialsHelper.parse(pasted)
                    apiId = p.apiId ?: pasted.filter { it.isDigit() }.ifBlank { apiId }
                },
            ) { apiId = it.filter { ch -> ch.isDigit() } }
            Field(
                label = "API Hash",
                value = apiHash,
                keyboardType = KeyboardType.Ascii,
                password = true,
                onPaste = {
                    val pasted = readClipboard(context)
                    val p = CredentialsHelper.parse(pasted)
                    apiHash = p.apiHash ?: pasted.trim()
                },
            ) { apiHash = it.trim() }

            AnimatedVisibility(visible = hint != null) {
                Text(
                    hint.orEmpty(),
                    color = Success,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = 8.dp),
                )
            }
        }

        PrimaryButton(
            onClick = {
                EnvStore.save(
                    dataDir,
                    mapOf(
                        "API_ID" to apiId.trim(),
                        "API_HASH" to apiHash.trim(),
                        "TELEGRAM_NOTIFY" to "0",
                    ),
                )
                onSaved()
            },
            enabled = canContinue,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("Продолжить", fontWeight = FontWeight.Bold)
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun StepRow(number: Int, title: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(28.dp)
                .clip(CircleShape)
                .background(Accent.copy(alpha = 0.2f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                number.toString(),
                color = Accent,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.labelLarge,
            )
        }
        Spacer(Modifier.width(10.dp))
        Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
    }
}

private fun readClipboard(context: android.content.Context): String {
    val cm = context.getSystemService<ClipboardManager>() ?: return ""
    val clip = cm.primaryClip ?: return ""
    if (clip.itemCount == 0) return ""
    return clip.getItemAt(0).coerceToText(context).toString()
}

@Composable
private fun HomePane(
    status: String,
    error: String,
    serviceRunning: Boolean,
    runtimeReady: Boolean,
    authKind: AuthBroker.PromptKind,
    bridgeProvider: () -> PythonBridge?,
    onStartService: () -> Unit,
    onStopService: () -> Unit,
    onSubmitAuth: (String) -> Unit,
    onOpenBatterySettings: () -> Unit,
    onFlash: (String) -> Unit,
    onNeedSettings: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    var dash by remember { mutableStateOf<JSONObject?>(null) }
    var busy by remember { mutableStateOf(false) }

    LaunchedEffect(runtimeReady) {
        while (runtimeReady) {
            val bridge = bridgeProvider()
            if (bridge != null) {
                val result = withContext(Dispatchers.IO) { bridge.callJson("get_dashboard") }
                if (result.ok) dash = result.asObject()
            }
            delay(1500)
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Panel {
            Text("Сервис", style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(8.dp))
            StatusBadge(resolveServiceStatus(status, serviceRunning, runtimeReady))
            if (error.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                Text(error, color = Danger, style = MaterialTheme.typography.bodyMedium)
            }
            Spacer(Modifier.height(12.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (!serviceRunning) {
                    PrimaryButton(onClick = onStartService) { Text("Старт", fontWeight = FontWeight.SemiBold) }
                } else {
                    SecondaryButton(onClick = onStopService) { Text("Стоп сервиса") }
                }
                QuietTextButton(onClick = onOpenBatterySettings) { Text("Батарея") }
            }
        }

        if (authKind != AuthBroker.PromptKind.NONE) {
            AuthPanel(authKind, onSubmitAuth)
        }

        if (runtimeReady) {
            val stats = dash?.optJSONObject("stats")
            val monitorOn = dash?.optBoolean("monitor_running") == true
            Panel {
                Text("Мониторинг", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(10.dp))
                StatusBadge(resolveMonitorStatus(monitorOn))
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    StatChip("Чаты", stats?.optInt("active_chats")?.toString() ?: "—")
                    StatChip("Слова", stats?.optInt("words")?.toString() ?: "—")
                    StatChip("Сегодня", stats?.optInt("matches_today")?.toString() ?: "—")
                }
                Spacer(Modifier.height(14.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    PrimaryButton(
                        enabled = !busy && !monitorOn,
                        onClick = {
                            busy = true
                            scope.launch {
                                val r = withContext(Dispatchers.IO) {
                                    bridgeProvider()?.callJson("start_monitor")
                                }
                                busy = false
                                if (r?.ok == true) onFlash("Мониторинг запущен")
                                else onFlash(r?.error ?: "Не удалось запустить")
                            }
                        },
                        modifier = Modifier.weight(1f),
                    ) { Text("Включить", fontWeight = FontWeight.SemiBold) }
                    SecondaryButton(
                        enabled = !busy && monitorOn,
                        onClick = {
                            busy = true
                            scope.launch {
                                withContext(Dispatchers.IO) {
                                    bridgeProvider()?.callJson("stop_monitor")
                                }
                                busy = false
                                onFlash("Мониторинг остановлен")
                            }
                        },
                        modifier = Modifier.weight(1f),
                    ) { Text("Выключить") }
                }
            }
        } else if (serviceRunning && authKind == AuthBroker.PromptKind.NONE) {
            Panel {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(10.dp))
                    Text("Подключение к Telegram…", color = OnMuted)
                }
            }
        } else if (!serviceRunning) {
            Panel {
                Text(
                    "Нажмите «Старт», войдите в Telegram — и управляйте чатами прямо в приложении.",
                    color = OnMuted,
                )
                QuietTextButton(onClick = onNeedSettings) { Text("Открыть настройки") }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun AuthPanel(kind: AuthBroker.PromptKind, onSubmit: (String) -> Unit) {
    var value by remember { mutableStateOf("") }
    val label = when (kind) {
        AuthBroker.PromptKind.PHONE -> "Номер телефона (+7…)"
        AuthBroker.PromptKind.CODE -> "Код из Telegram"
        AuthBroker.PromptKind.PASSWORD -> "Пароль 2FA"
        else -> ""
    }
    Panel {
        Text("Авторизация Telethon", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(8.dp))
        Field(
            label,
            value,
            if (kind == AuthBroker.PromptKind.PHONE) KeyboardType.Phone else KeyboardType.Text,
            password = kind == AuthBroker.PromptKind.PASSWORD,
        ) { value = it }
        PrimaryButton(
            onClick = {
                onSubmit(value.trim())
                value = ""
            },
            enabled = value.isNotBlank(),
            modifier = Modifier.fillMaxWidth(),
        ) { Text("Отправить", fontWeight = FontWeight.SemiBold) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ChatsPane(
    runtimeReady: Boolean,
    bridgeProvider: () -> PythonBridge?,
    onFlash: (String) -> Unit,
) {
    val scope = rememberCoroutineScope()
    var chats by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var showDiscover by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }

    fun reload() {
        scope.launch {
            loading = true
            val r = withContext(Dispatchers.IO) { bridgeProvider()?.callJson("list_chats") }
            chats = r?.asArray()?.toObjList().orEmpty()
            loading = false
        }
    }

    LaunchedEffect(runtimeReady) {
        if (runtimeReady) reload()
    }

    Box(Modifier.fillMaxSize()) {
        if (!runtimeReady) {
            NeedRuntime()
        } else {
            LazyColumn(
                contentPadding = PaddingValues(bottom = 88.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (loading && chats.isEmpty()) {
                    item { CircularProgressIndicator(modifier = Modifier.padding(24.dp)) }
                }
                items(chats, key = { it.getLong("chat_id") }) { chat ->
                    ChatRow(
                        chat = chat,
                        onToggle = {
                            scope.launch {
                                withContext(Dispatchers.IO) {
                                    bridgeProvider()?.callJson("toggle_chat", chat.getLong("chat_id"))
                                }
                                reload()
                            }
                        },
                        onDelete = {
                            scope.launch {
                                withContext(Dispatchers.IO) {
                                    bridgeProvider()?.callJson("remove_chat", chat.getLong("chat_id"))
                                }
                                onFlash("Чат удалён")
                                reload()
                            }
                        },
                    )
                }
                if (!loading && chats.isEmpty()) {
                    item {
                        Panel {
                            EmptyHint(
                                title = "Пока нет чатов",
                                body = "Добавьте группы из списка диалогов Telegram.",
                            )
                        }
                    }
                }
            }
            FloatingActionButton(
                onClick = { showDiscover = true },
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(16.dp),
                containerColor = Accent,
            ) { Icon(Icons.Outlined.Add, contentDescription = "Добавить") }
        }
    }

    if (showDiscover) {
        DiscoverSheet(
            bridgeProvider = bridgeProvider,
            onDismiss = { showDiscover = false },
            onAdded = {
                onFlash("Чат добавлен")
                showDiscover = false
                reload()
            },
        )
    }
}

@Composable
private fun ChatRow(chat: JSONObject, onToggle: () -> Unit, onDelete: () -> Unit) {
    val active = chat.optBoolean("is_active")
    Panel {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text(chat.optString("title"), style = MaterialTheme.typography.titleMedium)
                Text(
                    buildString {
                        append(chat.optString("chat_type"))
                        val u = chat.optString("username")
                        if (u.isNotBlank() && u != "null") append(" · @$u")
                    },
                    color = OnMuted,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
            FilterChip(
                selected = active,
                onClick = onToggle,
                label = { Text(if (active) "ON" else "OFF") },
            )
            IconButton(onClick = onDelete) {
                Icon(Icons.Outlined.Delete, contentDescription = "Удалить", tint = Danger)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DiscoverSheet(
    bridgeProvider: () -> PythonBridge?,
    onDismiss: () -> Unit,
    onAdded: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var page by remember { mutableIntStateOf(0) }
    var items by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var total by remember { mutableIntStateOf(0) }
    var loading by remember { mutableStateOf(true) }
    var ref by remember { mutableStateOf("") }

    fun load(p: Int) {
        scope.launch {
            loading = true
            val r = withContext(Dispatchers.IO) {
                bridgeProvider()?.callJson("list_dialogs", p)
            }
            val obj = r?.asObject()
            items = obj?.optJSONArray("items")?.toObjList().orEmpty()
            total = obj?.optInt("total") ?: 0
            page = p
            loading = false
        }
    }

    LaunchedEffect(Unit) { load(0) }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = SlateSurface,
    ) {
        Column(Modifier.padding(horizontal = 16.dp)) {
            Text("Мои диалоги", style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(
                value = ref,
                onValueChange = { ref = it },
                modifier = Modifier.fillMaxWidth(),
                label = { Text("@username / ссылка / id") },
                colors = fieldColors(),
            )
            QuietTextButton(
                onClick = {
                    scope.launch {
                        val r = withContext(Dispatchers.IO) {
                            bridgeProvider()?.callJson("add_chat_ref", ref.trim())
                        }
                        if (r?.ok == true) onAdded()
                    }
                },
                enabled = ref.isNotBlank(),
            ) { Text("Добавить по ссылке") }
            Spacer(Modifier.height(8.dp))
            if (loading) {
                CircularProgressIndicator(modifier = Modifier.padding(16.dp))
            } else {
                LazyColumn(
                    modifier = Modifier.height(360.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                ) {
                    items(items, key = { it.getLong("chat_id") }) { item ->
                        val monitored = item.optBoolean("monitored")
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clip(RoundedCornerShape(12.dp))
                                .background(SlateElevated)
                                .clickable(enabled = !monitored) {
                                    scope.launch {
                                        val r = withContext(Dispatchers.IO) {
                                            bridgeProvider()?.callJson(
                                                "add_chat",
                                                item.getLong("chat_id"),
                                            )
                                        }
                                        if (r?.ok == true) onAdded()
                                    }
                                }
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(item.optString("title"))
                                Text(item.optString("chat_type"), color = OnMuted)
                            }
                            Text(if (monitored) "✓" else "+", color = if (monitored) Success else Accent)
                        }
                    }
                }
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    QuietTextButton(onClick = { if (page > 0) load(page - 1) }, enabled = page > 0) {
                        Text("Назад")
                    }
                    Text("${page + 1} / ${((total + 7) / 8).coerceAtLeast(1)}", color = OnMuted)
                    QuietTextButton(
                        onClick = { if ((page + 1) * 8 < total) load(page + 1) },
                        enabled = (page + 1) * 8 < total,
                    ) { Text("Далее") }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun WordsPane(
    runtimeReady: Boolean,
    bridgeProvider: () -> PythonBridge?,
    onFlash: (String) -> Unit,
) {
    val scope = rememberCoroutineScope()
    var words by remember { mutableStateOf<List<String>>(emptyList()) }
    var draft by remember { mutableStateOf("") }

    fun reload() {
        scope.launch {
            val r = withContext(Dispatchers.IO) { bridgeProvider()?.callJson("list_words") }
            words = r?.asStringList().orEmpty()
        }
    }

    LaunchedEffect(runtimeReady) {
        if (runtimeReady) reload()
    }

    if (!runtimeReady) {
        NeedRuntime()
        return
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = draft,
                onValueChange = { draft = it },
                modifier = Modifier.weight(1f),
                label = { Text("Ключевое слово") },
                singleLine = true,
                shape = AppButtonShape,
                colors = fieldColors(),
            )
            PrimaryButton(
                onClick = {
                    scope.launch {
                        withContext(Dispatchers.IO) {
                            bridgeProvider()?.callJson("add_word", draft.trim())
                        }
                        draft = ""
                        onFlash("Слово добавлено")
                        reload()
                    }
                },
                enabled = draft.isNotBlank(),
            ) { Text("Добавить") }
        }
        Spacer(Modifier.height(16.dp))
        if (words.isEmpty()) {
            Panel {
                EmptyHint(
                    title = "Список пуст",
                    body = "Добавьте слова для поиска в чатах.",
                )
            }
        } else {
            FlowRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                words.forEach { word ->
                    KeywordChip(
                        word = word,
                        onRemove = {
                            scope.launch {
                                withContext(Dispatchers.IO) {
                                    bridgeProvider()?.callJson("remove_word", word)
                                }
                                reload()
                            }
                        },
                    )
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MatchesPane(runtimeReady: Boolean, bridgeProvider: () -> PythonBridge?) {
    val context = LocalContext.current
    var matches by remember { mutableStateOf<List<JSONObject>>(emptyList()) }

    LaunchedEffect(runtimeReady) {
        while (runtimeReady) {
            val r = withContext(Dispatchers.IO) {
                bridgeProvider()?.callJson("list_matches", 50)
            }
            matches = r?.asArray()?.toObjList().orEmpty()
            delay(2500)
        }
    }

    if (!runtimeReady) {
        NeedRuntime()
        return
    }

    LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(matches, key = { it.optInt("id") }) { m ->
            MatchRow(
                match = m,
                onOpen = {
                    val link = m.optString("message_link")
                    if (link.isNotBlank()) {
                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(link)))
                    }
                },
            )
        }
        if (matches.isEmpty()) {
            item {
                Panel {
                    EmptyHint(
                        title = "Журнал пуст",
                        body = "Совпадения появятся здесь и в уведомлениях.",
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun MatchRow(match: JSONObject, onOpen: () -> Unit) {
    val keywords = match.optString("keywords")
        .split(',')
        .map { it.trim() }
        .filter { it.isNotBlank() }
    val link = match.optString("message_link")
    val whenLabel = formatMatchTime(match.optString("created_at"))

    Panel {
        Row(verticalAlignment = Alignment.Top) {
            Column(Modifier.weight(1f)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        match.optString("chat_title"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    if (whenLabel.isNotBlank()) {
                        Text(
                            whenLabel,
                            color = OnMuted,
                            style = MaterialTheme.typography.labelLarge,
                        )
                    }
                }
                if (keywords.isNotEmpty()) {
                    Spacer(Modifier.height(8.dp))
                    FlowRow(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalArrangement = Arrangement.spacedBy(6.dp),
                    ) {
                        keywords.forEach { KeywordTag(it) }
                    }
                }
                Spacer(Modifier.height(8.dp))
                Text(
                    match.optString("text_preview"),
                    color = OnMuted,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 3,
                )
            }
            if (link.isNotBlank() && link != "null") {
                IconButton(onClick = onOpen) {
                    Icon(
                        Icons.Outlined.OpenInNew,
                        contentDescription = "Открыть сообщение",
                        tint = Accent,
                    )
                }
            }
        }
    }
}

@Composable
private fun MorePane(
    dataDir: File,
    runtimeReady: Boolean,
    bridgeProvider: () -> PythonBridge?,
    onFlash: (String) -> Unit,
    onOpenBatterySettings: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val stored = remember { EnvStore.load(dataDir) }
    var apiId by remember { mutableStateOf(stored["API_ID"].orEmpty()) }
    var apiHash by remember { mutableStateOf(stored["API_HASH"].orEmpty()) }
    var botToken by remember { mutableStateOf(stored["BOT_TOKEN"].orEmpty()) }
    var telegramNotify by remember {
        mutableStateOf(stored["TELEGRAM_NOTIFY"] == "1")
    }
    var poll by remember { mutableStateOf(stored["POLL_INTERVAL"] ?: "10") }
    var notifyMode by remember { mutableStateOf("instant") }
    var scanning by remember { mutableStateOf(false) }

    LaunchedEffect(runtimeReady) {
        if (!runtimeReady) return@LaunchedEffect
        val r = withContext(Dispatchers.IO) { bridgeProvider()?.callJson("get_app_settings") }
        val obj = r?.asObject() ?: return@LaunchedEffect
        notifyMode = obj.optString("notify_mode", "instant")
        poll = obj.optInt("poll_interval", 10).toString()
        telegramNotify = obj.optBoolean("telegram_notify")
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Panel {
            Text("Telegram API", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Spacer(Modifier.height(6.dp))
            Text(
                "Не хватает данных? Откройте страницу и вставьте из буфера.",
                color = OnMuted,
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                SecondaryButton(
                    onClick = {
                        context.startActivity(
                            Intent(Intent.ACTION_VIEW, Uri.parse(CredentialsHelper.MY_TELEGRAM_APPS)),
                        )
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Outlined.OpenInBrowser, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Получить")
                }
                SecondaryButton(
                    onClick = {
                        val parsed = CredentialsHelper.parse(readClipboard(context))
                        if (!parsed.hasAnything) {
                            onFlash("В буфере нет API ID / Hash")
                        } else {
                            parsed.apiId?.let { apiId = it }
                            parsed.apiHash?.let { apiHash = it }
                            onFlash("Вставлено из буфера")
                        }
                    },
                    modifier = Modifier.weight(1f),
                ) {
                    Icon(Icons.Outlined.ContentPaste, null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(6.dp))
                    Text("Вставить")
                }
            }
            Spacer(Modifier.height(8.dp))
            Field("API ID", apiId, KeyboardType.Number) { apiId = it.filter { ch -> ch.isDigit() } }
            Field("API Hash", apiHash, KeyboardType.Ascii, password = true) { apiHash = it.trim() }
            Field("BOT_TOKEN (опционально)", botToken, KeyboardType.Password, password = true) {
                botToken = it
            }
            QuietTextButton(
                onClick = {
                    context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(CredentialsHelper.BOT_FATHER)))
                },
            ) {
                Icon(Icons.Outlined.OpenInBrowser, null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Открыть @BotFather для токена")
            }
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(Modifier.weight(1f)) {
                    Text("Дублировать в Telegram")
                    Text("Нужен BOT_TOKEN", color = OnMuted, style = MaterialTheme.typography.bodyMedium)
                }
                Switch(
                    checked = telegramNotify,
                    onCheckedChange = { telegramNotify = it },
                    colors = SwitchDefaults.colors(checkedTrackColor = Accent),
                )
            }
            PrimaryButton(
                onClick = {
                    EnvStore.save(
                        dataDir,
                        mapOf(
                            "API_ID" to apiId,
                            "API_HASH" to apiHash,
                            "BOT_TOKEN" to botToken,
                            "TELEGRAM_NOTIFY" to if (telegramNotify) "1" else "0",
                            "POLL_INTERVAL" to poll,
                        ),
                    )
                    onFlash("Сохранено. Перезапустите сервис при смене токена.")
                },
                modifier = Modifier.fillMaxWidth(),
            ) { Text("Сохранить .env", fontWeight = FontWeight.SemiBold) }
        }

        if (runtimeReady) {
            Panel {
                Text("Параметры мониторинга", style = MaterialTheme.typography.titleMedium)
                Spacer(Modifier.height(8.dp))
                Field("Интервал опроса (сек)", poll, KeyboardType.Number) { poll = it }
                Text("Режим уведомлений Telegram", color = OnMuted)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf(
                        "instant" to "Сразу",
                        "digest_15" to "15 мин",
                        "digest_60" to "Час",
                    ).forEach { (mode, label) ->
                        FilterChip(
                            selected = notifyMode == mode,
                            onClick = { notifyMode = mode },
                            label = { Text(label) },
                        )
                    }
                }
                PrimaryButton(
                    onClick = {
                        scope.launch {
                            val payload = JSONObject()
                                .put("poll_interval", poll.toIntOrNull() ?: 10)
                                .put("notify_mode", notifyMode)
                                .put("telegram_notify", telegramNotify)
                                .toString()
                            withContext(Dispatchers.IO) {
                                bridgeProvider()?.callJson("update_app_settings", payload)
                            }
                            onFlash("Настройки применены")
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Применить", fontWeight = FontWeight.SemiBold) }
            }

            Panel {
                Text("Скан истории", style = MaterialTheme.typography.titleMedium)
                Text("Найти совпадения в уже существующих сообщениях.", color = OnMuted)
                Spacer(Modifier.height(8.dp))
                PrimaryButton(
                    enabled = !scanning,
                    onClick = {
                        scanning = true
                        scope.launch {
                            val r = withContext(Dispatchers.IO) {
                                bridgeProvider()?.callJson("start_scan", 0)
                            }
                            scanning = false
                            if (r?.ok == true) {
                                val d = r.asObject()
                                onFlash(
                                    "Готово: найдено ${d?.optInt("matches_found")}, " +
                                        "уведомлений ${d?.optInt("matches_sent")}",
                                )
                            } else {
                                onFlash(r?.error ?: "Ошибка скана")
                            }
                        }
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(if (scanning) "Сканирование…" else "Запустить скан")
                }
            }
        }

        Panel {
            Text("Система", style = MaterialTheme.typography.titleMedium)
            QuietTextButton(onClick = onOpenBatterySettings) {
                Icon(Icons.Outlined.Settings, null)
                Spacer(Modifier.width(8.dp))
                Text("Исключить из оптимизации батареи")
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun NeedRuntime() {
    Panel {
        EmptyHint(
            title = "Сервис не запущен",
            body = "Откройте «Главная» и нажмите Старт, затем войдите в Telegram.",
        )
    }
}

@Composable
private fun Panel(content: @Composable () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(18.dp))
            .background(
                Brush.verticalGradient(
                    listOf(SlateSurface, SlateElevated.copy(alpha = 0.55f)),
                ),
            )
            .border(1.dp, Accent.copy(alpha = 0.12f), RoundedCornerShape(18.dp))
            .padding(16.dp),
        content = { content() },
    )
}

@Composable
private fun StatChip(label: String, value: String) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(SlateElevated)
            .padding(horizontal = 12.dp, vertical = 8.dp),
    ) {
        Text(value, style = MaterialTheme.typography.titleLarge, color = Accent)
        Text(label, color = OnMuted, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun Field(
    label: String,
    value: String,
    keyboardType: KeyboardType,
    password: Boolean = false,
    onPaste: (() -> Unit)? = null,
    onChange: (String) -> Unit,
) {
    var showPassword by remember { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        visualTransformation = if (password && !showPassword) {
            PasswordVisualTransformation()
        } else {
            VisualTransformation.None
        },
        trailingIcon = {
            Row {
                if (password) {
                    IconButton(onClick = { showPassword = !showPassword }) {
                        Icon(
                            if (showPassword) Icons.Outlined.VisibilityOff else Icons.Outlined.Visibility,
                            contentDescription = null,
                            tint = OnMuted,
                        )
                    }
                }
                if (onPaste != null) {
                    IconButton(onClick = onPaste) {
                        Icon(Icons.Outlined.ContentPaste, contentDescription = "Вставить", tint = Accent)
                    }
                }
            }
        },
        shape = RoundedCornerShape(14.dp),
        colors = fieldColors(),
    )
}

@Composable
private fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Accent,
    unfocusedBorderColor = OnMuted.copy(alpha = 0.28f),
    focusedLabelColor = Accent,
    unfocusedLabelColor = OnMuted,
    cursorColor = Accent,
    focusedContainerColor = SlateBg.copy(alpha = 0.35f),
    unfocusedContainerColor = Color.Transparent,
)

private fun JSONArray.toObjList(): List<JSONObject> =
    List(length()) { getJSONObject(it) }
