package com.tgchatmonitor.app

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import java.io.File

class PythonBridge(
    context: Context,
    private val authBroker: AuthBroker,
) {
    private val dataDir: File = context.filesDir
    private val module: PyObject by lazy {
        Python.getInstance().getModule("android_bridge")
    }

    fun configure() {
        module.callAttr("configure", dataDir.absolutePath, authBroker)
    }

    fun start(): Boolean {
        configure()
        return module.callAttr("start").toBoolean()
    }

    fun stop() {
        module.callAttr("stop")
    }

    fun status(): String = module.callAttr("get_status").toString()

    fun lastError(): String = module.callAttr("get_last_error").toString()

    fun isRunning(): Boolean = module.callAttr("is_running").toBoolean()

    fun dataDirectory(): File = dataDir
}
