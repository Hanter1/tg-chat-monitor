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
import androidx.core.content.getSystemService
import com.chaquo.python.Python
import com.tgchatmonitor.app.ui.AppRoot
import com.tgchatmonitor.app.ui.theme.MonitorTheme

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
            MonitorTheme {
                AppRoot(
                    dataDir = filesDir,
                    onStartService = { MonitorService.start(this) },
                    onStopService = { MonitorService.stop(this) },
                    onSubmitAuth = { MonitorService.submitAuth(this, it) },
                    onOpenBatterySettings = { openBatterySettings() },
                    authBrokerProvider = { MonitorService.instanceAuthBroker },
                    serviceRunningProvider = { MonitorService.isRunning },
                    bridgeProvider = { MonitorService.instanceBridge },
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
