package com.tgchatmonitor.app

import android.content.Context
import com.chaquo.python.PyObject
import com.chaquo.python.Python
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class PythonBridge(
    context: Context,
    private val authBroker: AuthBroker,
    private val notificationBroker: NotificationBroker,
) {
    private val dataDir: File = context.filesDir
    private val module: PyObject by lazy {
        Python.getInstance().getModule("android_bridge")
    }

    fun configure() {
        module.callAttr(
            "configure",
            dataDir.absolutePath,
            authBroker,
            notificationBroker,
        )
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

    fun callJson(method: String, vararg args: Any): ApiResult {
        return try {
            val raw = if (args.isEmpty()) {
                module.callAttr(method).toString()
            } else {
                module.callAttr(method, *args).toString()
            }
            ApiResult.parse(raw)
        } catch (e: Exception) {
            ApiResult(ok = false, error = e.message ?: "Python error", data = null)
        }
    }
}

data class ApiResult(
    val ok: Boolean,
    val error: String?,
    val data: Any?,
    val code: String? = null,
) {
    companion object {
        fun parse(raw: String): ApiResult {
            val obj = JSONObject(raw)
            val ok = obj.optBoolean("ok", false)
            return ApiResult(
                ok = ok,
                error = if (ok) null else obj.optString("error", "error"),
                code = if (obj.has("code")) obj.optString("code") else null,
                data = if (obj.has("data") && !obj.isNull("data")) obj.get("data") else null,
            )
        }
    }

    fun asObject(): JSONObject? = data as? JSONObject
    fun asArray(): JSONArray? = data as? JSONArray
    fun asStringList(): List<String> {
        val arr = asArray() ?: return emptyList()
        return List(arr.length()) { arr.getString(it) }
    }
}
