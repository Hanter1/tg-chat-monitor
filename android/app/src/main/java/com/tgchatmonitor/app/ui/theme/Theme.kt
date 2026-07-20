package com.tgchatmonitor.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.Typography
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

val SlateBg = Color(0xFF0B1220)
val SlateSurface = Color(0xFF121A27)
val SlateElevated = Color(0xFF1A2436)
val Accent = Color(0xFF2AABEE)
val AccentMuted = Color(0xFF1B6F9A)
val OnSurface = Color(0xFFE8EEF7)
val OnMuted = Color(0xFF9AA8BC)
val Success = Color(0xFF3DDC97)
val Danger = Color(0xFFFF6B7A)

private val ColorScheme = darkColorScheme(
    primary = Accent,
    onPrimary = Color(0xFF041018),
    secondary = AccentMuted,
    background = SlateBg,
    surface = SlateSurface,
    surfaceVariant = SlateElevated,
    onBackground = OnSurface,
    onSurface = OnSurface,
    onSurfaceVariant = OnMuted,
    outline = Color(0xFF2C3A52),
    error = Danger,
)

private val AppTypography = Typography(
    displaySmall = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Bold,
        fontSize = 28.sp,
        letterSpacing = (-0.5).sp,
    ),
    headlineMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 22.sp,
    ),
    titleLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 18.sp,
    ),
    titleMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Medium,
        fontSize = 16.sp,
    ),
    bodyLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 15.sp,
        lineHeight = 22.sp,
    ),
    bodyMedium = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.Normal,
        fontSize = 14.sp,
        lineHeight = 20.sp,
    ),
    labelLarge = TextStyle(
        fontFamily = FontFamily.SansSerif,
        fontWeight = FontWeight.SemiBold,
        fontSize = 14.sp,
    ),
)

@Composable
fun MonitorTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ColorScheme,
        typography = AppTypography,
        content = content,
    )
}
