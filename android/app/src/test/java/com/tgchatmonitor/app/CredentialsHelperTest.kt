package com.tgchatmonitor.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class CredentialsHelperTest {
    @Test
    fun parsesMyTelegramPageSnippet() {
        val text = """
            App api_id:
            31234567
            App api_hash:
            a1b2c3d4e5f6789012345678abcdef01
        """.trimIndent()
        val p = CredentialsHelper.parse(text)
        assertEquals("31234567", p.apiId)
        assertEquals("a1b2c3d4e5f6789012345678abcdef01", p.apiHash)
    }

    @Test
    fun parsesLabeledInline() {
        val p = CredentialsHelper.parse("api_id: 42\napi_hash: 0123456789abcdef0123456789abcdef")
        assertEquals("42", p.apiId)
        assertEquals("0123456789abcdef0123456789abcdef", p.apiHash)
    }

    @Test
    fun parsesBareValues() {
        assertEquals("99", CredentialsHelper.parse("99").apiId)
        assertEquals(
            "0123456789abcdef0123456789abcdef",
            CredentialsHelper.parse("0123456789abcdef0123456789abcdef").apiHash,
        )
        assertNull(CredentialsHelper.parse("hello").apiId)
    }
}
