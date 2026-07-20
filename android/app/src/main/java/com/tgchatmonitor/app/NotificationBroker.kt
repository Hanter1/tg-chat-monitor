package com.tgchatmonitor.app

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import org.json.JSONObject

/**
 * Called from Python worker thread via Chaquopy: onMatch(json).
 */
class NotificationBroker(private val context: Context) {
    private val handler = Handler(Looper.getMainLooper())
    private var nextId = 1000

    @Suppress("unused") // invoked from Python
    fun onMatch(json: String) {
        handler.post { showMatch(json) }
    }

    private fun showMatch(json: String) {
        try {
            val obj = JSONObject(json)
            val title = obj.optString("chat_title", "Совпадение")
            val text = obj.optString("text", "")
            val keywords = obj.optJSONArray("matched_keywords")
            val kw = buildString {
                if (keywords != null) {
                    for (i in 0 until keywords.length()) {
                        if (i > 0) append(", ")
                        append(keywords.optString(i))
                    }
                }
            }
            val link = obj.optString("message_link", "")
            val body = buildString {
                if (kw.isNotEmpty()) append("🔑 $kw\n")
                append(text.take(180))
            }

            val openIntent = if (link.isNotBlank()) {
                Intent(Intent.ACTION_VIEW, Uri.parse(link))
            } else {
                Intent(context, MainActivity::class.java)
            }
            val pending = PendingIntent.getActivity(
                context,
                nextId,
                openIntent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

            val notification = NotificationCompat.Builder(context, MATCH_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_launcher_foreground)
                .setContentTitle("🔔 $title")
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(pending)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build()

            val manager = context.getSystemService(NotificationManager::class.java) ?: return
            manager.notify(nextId++, notification)
        } catch (_: Exception) {
            // ignore malformed payloads
        }
    }

    companion object {
        const val MATCH_CHANNEL_ID = "matches_channel"
    }
}
