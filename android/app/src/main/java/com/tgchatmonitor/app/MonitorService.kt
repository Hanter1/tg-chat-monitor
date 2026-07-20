package com.tgchatmonitor.app

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat

class MonitorService : Service() {
    private val handler = Handler(Looper.getMainLooper())
    private var bridge: PythonBridge? = null
    private var authBroker: AuthBroker? = null

    private val pollStatus = object : Runnable {
        override fun run() {
            val b = bridge ?: return
            val status = b.status()
            val error = b.lastError()
            val text = when (status) {
                "running" -> getString(R.string.notification_text)
                "authorizing" -> "Ожидание входа в Telegram…"
                "starting" -> getString(R.string.notification_starting)
                "error" -> "Ошибка: ${error.take(80)}"
                else -> "Статус: $status"
            }
            val manager = getSystemService(NOTIFICATION_SERVICE) as android.app.NotificationManager
            manager.notify(NOTIFICATION_ID, buildNotification(text))

            if (status == "error" || status == "stopped") {
                stopSelf()
                return
            }
            handler.postDelayed(this, 1500)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        when (intent?.action) {
            ACTION_STOP -> {
                bridge?.stop()
                stopForeground(STOP_FOREGROUND_REMOVE)
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_SUBMIT_AUTH -> {
                val value = intent.getStringExtra(EXTRA_AUTH_VALUE).orEmpty()
                authBroker?.submitAnswer(value)
                return START_STICKY
            }
        }

        if (bridge == null) {
            val broker = AuthBroker()
            authBroker = broker
            instanceAuthBroker = broker
            bridge = PythonBridge(this, broker)
        }

        ServiceCompat.startForeground(
            this,
            NOTIFICATION_ID,
            buildNotification(getString(R.string.notification_starting)),
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            } else {
                0
            },
        )

        val started = bridge?.start() == true
        if (!started && bridge?.isRunning() != true) {
            // already running or failed to start thread
        }

        handler.removeCallbacks(pollStatus)
        handler.post(pollStatus)
        isRunning = true
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(pollStatus)
        bridge?.stop()
        isRunning = false
        instanceAuthBroker = null
        super.onDestroy()
    }

    private fun buildNotification(text: String): Notification {
        val openIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val stopIntent = PendingIntent.getService(
            this,
            1,
            Intent(this, MonitorService::class.java).setAction(ACTION_STOP),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(text)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(openIntent)
            .setOngoing(true)
            .addAction(0, "Стоп", stopIntent)
            .setOnlyAlertOnce(true)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "monitor_channel"
        const val NOTIFICATION_ID = 42
        const val ACTION_STOP = "com.tgchatmonitor.app.STOP"
        const val ACTION_SUBMIT_AUTH = "com.tgchatmonitor.app.SUBMIT_AUTH"
        const val EXTRA_AUTH_VALUE = "auth_value"

        @Volatile
        var isRunning: Boolean = false
            private set

        @Volatile
        var instanceAuthBroker: AuthBroker? = null
            private set

        fun start(context: Context) {
            val intent = Intent(context, MonitorService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            context.startService(
                Intent(context, MonitorService::class.java).setAction(ACTION_STOP),
            )
        }

        fun submitAuth(context: Context, value: String) {
            context.startService(
                Intent(context, MonitorService::class.java)
                    .setAction(ACTION_SUBMIT_AUTH)
                    .putExtra(EXTRA_AUTH_VALUE, value),
            )
        }
    }
}
