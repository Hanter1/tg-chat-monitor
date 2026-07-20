package com.tgchatmonitor.app

import com.tgchatmonitor.app.ui.formatMatchTime
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

class FormatMatchTimeTest {
    @Test
    fun emptyAndNull() {
        assertEquals("", formatMatchTime(null))
        assertEquals("", formatMatchTime(""))
        assertEquals("", formatMatchTime("null"))
    }

    @Test
    fun todayShowsTimeOnly() {
        val now = LocalDateTime.now(ZoneId.systemDefault())
        val iso = now.atZone(ZoneId.systemDefault()).toInstant().toString()
        val formatted = formatMatchTime(iso)
        assertEquals(now.format(DateTimeFormatter.ofPattern("HH:mm")), formatted)
    }

    @Test
    fun yesterdayPrefix() {
        val yesterday = LocalDate.now().minusDays(1).atTime(15, 30)
            .atZone(ZoneId.systemDefault()).toInstant().toString()
        assertEquals("вчера 15:30", formatMatchTime(yesterday))
    }

    @Test
    fun naiveUtcIsoWithoutZ() {
        val raw = "2024-01-15T12:30:45.123456"
        val formatted = formatMatchTime(raw)
        assertTrue(formatted.isNotBlank())
        // Converted from UTC to local — just ensure it parses and formats.
        val local = LocalDateTime.parse("2024-01-15T12:30:45")
            .toInstant(ZoneOffset.UTC)
            .atZone(ZoneId.systemDefault())
        val expected = if (local.toLocalDate() == LocalDate.now()) {
            local.format(DateTimeFormatter.ofPattern("HH:mm"))
        } else if (local.toLocalDate() == LocalDate.now().minusDays(1)) {
            "вчера ${local.format(DateTimeFormatter.ofPattern("HH:mm"))}"
        } else {
            local.format(DateTimeFormatter.ofPattern("dd.MM HH:mm"))
        }
        assertEquals(expected, formatted)
    }
}
