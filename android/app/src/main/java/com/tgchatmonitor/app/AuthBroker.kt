package com.tgchatmonitor.app

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/**
 * Blocking bridge for Telethon login prompts (called from Python worker thread).
 * Do not hold a monitor lock across await — UI thread must be able to submitAnswer().
 */
class AuthBroker {
    enum class PromptKind { PHONE, CODE, PASSWORD, NONE }

    @Volatile
    var pendingKind: PromptKind = PromptKind.NONE
        private set

    private val latchRef = AtomicReference<CountDownLatch?>(null)
    private val answerRef = AtomicReference<String?>(null)
    private val gate = Object()

    fun requestPhone(): String = request(PromptKind.PHONE)

    fun requestCode(): String = request(PromptKind.CODE)

    fun requestPassword(): String = request(PromptKind.PASSWORD)

    fun submitAnswer(value: String) {
        answerRef.set(value.trim())
        latchRef.get()?.countDown()
    }

    fun cancel() {
        answerRef.set("")
        latchRef.get()?.countDown()
        pendingKind = PromptKind.NONE
    }

    private fun request(kind: PromptKind): String {
        val latch = CountDownLatch(1)
        synchronized(gate) {
            pendingKind = kind
            answerRef.set(null)
            latchRef.set(latch)
        }
        val ok = latch.await(10, TimeUnit.MINUTES)
        synchronized(gate) {
            pendingKind = PromptKind.NONE
        }
        if (!ok) {
            throw IllegalStateException("Таймаут ожидания ввода ($kind)")
        }
        val value = answerRef.get().orEmpty()
        if (value.isBlank()) {
            throw IllegalStateException("Авторизация отменена")
        }
        return value
    }
}
