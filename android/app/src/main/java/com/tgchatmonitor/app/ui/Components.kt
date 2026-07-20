package com.tgchatmonitor.app.ui

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.tgchatmonitor.app.ui.theme.Accent
import com.tgchatmonitor.app.ui.theme.Danger
import com.tgchatmonitor.app.ui.theme.OnMuted
import com.tgchatmonitor.app.ui.theme.OnSurface
import com.tgchatmonitor.app.ui.theme.SlateElevated
import com.tgchatmonitor.app.ui.theme.Success
import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

val AppButtonShape = RoundedCornerShape(14.dp)
val AppButtonHeight = 48.dp

enum class StatusTone { Ready, Busy, Warning, Error, Idle }

data class StatusInfo(
    val label: String,
    val tone: StatusTone,
    val pulse: Boolean = false,
)

fun resolveServiceStatus(
    status: String,
    serviceRunning: Boolean,
    runtimeReady: Boolean,
): StatusInfo = when {
    runtimeReady -> StatusInfo("Подключено", StatusTone.Ready)
    status == "authorizing" -> StatusInfo("Вход в Telegram…", StatusTone.Busy, pulse = true)
    status == "starting" -> StatusInfo("Запуск…", StatusTone.Busy, pulse = true)
    status == "error" -> StatusInfo("Ошибка", StatusTone.Error)
    serviceRunning -> StatusInfo("Сервис работает", StatusTone.Busy, pulse = true)
    else -> StatusInfo("Остановлен", StatusTone.Idle)
}

fun resolveMonitorStatus(monitorOn: Boolean): StatusInfo =
    if (monitorOn) {
        StatusInfo("Мониторинг включён", StatusTone.Ready, pulse = true)
    } else {
        StatusInfo("Мониторинг выключен", StatusTone.Idle)
    }

@Composable
fun StatusBadge(
    info: StatusInfo,
    modifier: Modifier = Modifier,
) {
    val color = when (info.tone) {
        StatusTone.Ready -> Success
        StatusTone.Busy -> Accent
        StatusTone.Warning -> Color(0xFFFFB020)
        StatusTone.Error -> Danger
        StatusTone.Idle -> OnMuted
    }
    val transition = rememberInfiniteTransition(label = "status-pulse")
    val pulsed by transition.animateFloat(
        initialValue = 0.45f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(900),
            repeatMode = RepeatMode.Reverse,
        ),
        label = "dot-alpha",
    )
    val alpha = if (info.pulse) pulsed else 1f

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(color.copy(alpha = 0.14f))
            .padding(horizontal = 10.dp, vertical = 5.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(color.copy(alpha = alpha)),
        )
        Spacer(Modifier.width(8.dp))
        Text(
            info.label,
            color = color,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

@Composable
fun PrimaryButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    contentPadding: PaddingValues = ButtonDefaults.ContentPadding,
    content: @Composable RowScope.() -> Unit,
) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .height(AppButtonHeight)
            .defaultMinSize(minHeight = AppButtonHeight),
        shape = AppButtonShape,
        contentPadding = contentPadding,
        colors = ButtonDefaults.buttonColors(
            containerColor = Accent,
            contentColor = Color(0xFF041018),
            disabledContainerColor = SlateElevated,
            disabledContentColor = OnMuted,
        ),
        content = content,
    )
}

@Composable
fun SecondaryButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable RowScope.() -> Unit,
) {
    OutlinedButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier
            .height(AppButtonHeight)
            .defaultMinSize(minHeight = AppButtonHeight),
        shape = AppButtonShape,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = Accent),
        content = content,
    )
}

@Composable
fun QuietTextButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    content: @Composable RowScope.() -> Unit,
) {
    TextButton(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.height(40.dp),
        content = content,
    )
}

@Composable
fun KeywordChip(
    word: String,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .clip(RoundedCornerShape(50))
            .background(SlateElevated)
            .padding(start = 12.dp, end = 4.dp, top = 4.dp, bottom = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            word,
            color = OnSurface,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.Medium,
        )
        IconButton(
            onClick = onRemove,
            modifier = Modifier.size(28.dp),
        ) {
            Icon(
                Icons.Outlined.Close,
                contentDescription = "Удалить",
                tint = OnMuted,
                modifier = Modifier.size(16.dp),
            )
        }
    }
}

@Composable
fun KeywordTag(
    word: String,
    modifier: Modifier = Modifier,
) {
    Text(
        word,
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(Accent.copy(alpha = 0.16f))
            .padding(horizontal = 8.dp, vertical = 3.dp),
        color = Accent,
        style = MaterialTheme.typography.labelLarge,
        fontWeight = FontWeight.SemiBold,
    )
}

fun formatMatchTime(raw: String?): String {
    if (raw.isNullOrBlank() || raw == "null") return ""
    return try {
        val instant = parseInstant(raw)
        val zoned = instant.atZone(ZoneId.systemDefault())
        val today = LocalDate.now()
        val time = zoned.format(DateTimeFormatter.ofPattern("HH:mm"))
        when (zoned.toLocalDate()) {
            today -> time
            today.minusDays(1) -> "вчера $time"
            else -> zoned.format(DateTimeFormatter.ofPattern("dd.MM HH:mm"))
        }
    } catch (_: Exception) {
        raw.take(16)
    }
}

private fun parseInstant(raw: String): Instant {
    runCatching { return Instant.parse(raw) }
    runCatching { return Instant.parse(raw + "Z") }
    val trimmed = raw.substringBefore('.').take(19)
    return LocalDateTime.parse(trimmed).toInstant(ZoneOffset.UTC)
}

@Composable
fun EmptyHint(
    title: String,
    body: String,
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Text(title, style = MaterialTheme.typography.titleMedium, color = OnSurface)
        Text(body, color = OnMuted, style = MaterialTheme.typography.bodyMedium)
    }
}
