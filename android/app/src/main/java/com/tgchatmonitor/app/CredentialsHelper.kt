package com.tgchatmonitor.app

/**
 * Парсит API_ID / API_HASH из текста страницы my.telegram.org или буфера.
 */
object CredentialsHelper {
    const val MY_TELEGRAM_APPS = "https://my.telegram.org/apps"
    const val BOT_FATHER = "https://t.me/BotFather"

    private val idPattern = Regex(
        """(?is)(?:app\s+)?api[_\s-]?id\D{0,40}?(\d{4,12})""",
    )
    private val hashPattern = Regex(
        """(?is)(?:app\s+)?api[_\s-]?hash\D{0,40}?([a-f0-9]{32})""",
    )
    private val bareHash = Regex("""(?i)^[a-f0-9]{32}$""")
    private val bareId = Regex("""^\d{4,12}$""")

    data class Parsed(
        val apiId: String? = null,
        val apiHash: String? = null,
    ) {
        val hasAnything: Boolean get() = !apiId.isNullOrBlank() || !apiHash.isNullOrBlank()
    }

    fun parse(raw: String): Parsed {
        val text = raw.trim().replace('\u00a0', ' ')
        if (text.isEmpty()) return Parsed()

        val id = idPattern.find(text)?.groupValues?.get(1)
        val hash = hashPattern.find(text)?.groupValues?.get(1)?.lowercase()

        if (id != null || hash != null) {
            return Parsed(apiId = id, apiHash = hash)
        }

        return when {
            bareId.matches(text) -> Parsed(apiId = text)
            bareHash.matches(text) -> Parsed(apiHash = text.lowercase())
            else -> Parsed()
        }
    }
}
