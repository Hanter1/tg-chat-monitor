package com.tgchatmonitor.app

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Canvas
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
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
                        if (i > 0) append(" · ")
                        append(keywords.optString(i))
                    }
                }
            }
            val link = obj.optString("message_link", "")
            val body = buildString {
                if (kw.isNotEmpty()) {
                    append("Слова: ")
                    append(kw)
                    append('\n')
                }
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

            val builder = NotificationCompat.Builder(context, MATCH_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setColor(BRAND_COLOR)
                .setContentTitle(title)
                .setContentText(if (kw.isNotEmpty()) "$kw — ${text.take(80)}" else text.take(100))
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setContentIntent(pending)
                .setAutoCancel(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setCategory(NotificationCompat.CATEGORY_MESSAGE)

            largeIconBitmap()?.let { builder.setLargeIcon(it) }

            val manager = context.getSystemService(NotificationManager::class.java) ?: return
            manager.notify(nextId++, builder.build())
        } catch (_: Exception) {
            // ignore malformed payloads
        }
    }

    private fun largeIconBitmap(): Bitmap? {
        val drawable = ContextCompat.getDrawable(context, R.mipmap.ic_launcher)
            ?: ContextCompat.getDrawable(context, R.drawable.ic_notification_large)
            ?: return null
        val size = 192
        val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        drawable.setBounds(0, 0, size, size)
        drawable.draw(canvas)
        return bitmap
    }

    companion object {
        const val MATCH_CHANNEL_ID = "matches_channel"
        private const val BRAND_COLOR = 0xFF2AABEE.toInt()
    }
}
